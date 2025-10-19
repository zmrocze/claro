"""
Middleware for request validation and rate limiting
"""

import time
import logging
from typing import Dict
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from asgi_correlation_id import CorrelationIdMiddleware
from slowapi.errors import RateLimitExceeded
from backend.exceptions import CarloError, get_status_code

# Rate limiting
logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
  """
  Rate limiting middleware to prevent abuse
  """

  def __init__(
    self,
    app,
    requests_per_minute: int = 60,
    requests_per_hour: int = 1000,
    burst_size: int = 10,
  ):
    """
    Initialize rate limiter

    Args:
      app: FastAPI application
      requests_per_minute: Max requests per minute per IP
      requests_per_hour: Max requests per hour per IP
      burst_size: Max burst requests allowed
    """
    super().__init__(app)
    self.requests_per_minute = requests_per_minute
    self.requests_per_hour = requests_per_hour
    self.burst_size = burst_size

    # Store request timestamps per IP
    self.request_history: Dict[str, deque] = defaultdict(
      lambda: deque(maxlen=requests_per_hour)
    )

    # Burst tracking
    self.burst_tracker: Dict[str, int] = defaultdict(int)
    self.burst_reset: Dict[str, datetime] = {}

  def get_client_ip(self, request: Request) -> str:
    """Get client IP address"""
    # Check for forwarded IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
      return forwarded.split(",")[0].strip()

    # Check for real IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
      return real_ip

    # Fall back to client host
    return request.client.host if request.client else "unknown"

  async def dispatch(self, request: Request, call_next):
    """Process the request with rate limiting"""

    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
      return await call_next(request)

    client_ip = self.get_client_ip(request)
    now = datetime.now()

    # Clean old entries
    self._clean_old_entries(client_ip, now)

    # Check burst limit
    if not self._check_burst_limit(client_ip, now):
      logger.warning(f"Burst limit exceeded for {client_ip}")
      error = CarloError(
        description="Too many requests in a short time. Please slow down and try again in 10 seconds.",
        name="BURST_LIMIT_EXCEEDED",
        source="rate_limiter",
      )
      return JSONResponse(
        status_code=429,
        content=error.to_response().model_dump(),
      )

    # Check rate limits
    if not self._check_rate_limits(client_ip, now):
      logger.warning(f"Rate limit exceeded for {client_ip}")
      error = CarloError(
        description="Rate limit exceeded. Please try again in 60 seconds.",
        name="RATE_LIMIT_EXCEEDED",
        source="rate_limiter",
      )
      return JSONResponse(
        status_code=429,
        content=error.to_response().model_dump(),
      )

    # Record this request
    self.request_history[client_ip].append(now)

    # Process request
    try:
      response = await call_next(request)
      return response
    except Exception as e:
      logger.error(f"Error processing request: {e}")
      raise

  def _clean_old_entries(self, client_ip: str, now: datetime) -> None:
    """Remove old request entries"""
    history = self.request_history[client_ip]
    one_hour_ago = now - timedelta(hours=1)

    # Remove entries older than 1 hour
    while history and history[0] < one_hour_ago:
      history.popleft()

  def _check_burst_limit(self, client_ip: str, now: datetime) -> bool:
    """Check if burst limit is exceeded"""
    # Reset burst counter if needed
    if client_ip in self.burst_reset:
      if now > self.burst_reset[client_ip]:
        self.burst_tracker[client_ip] = 0
        del self.burst_reset[client_ip]

    # Check burst
    if self.burst_tracker[client_ip] >= self.burst_size:
      # Set reset time if not set
      if client_ip not in self.burst_reset:
        self.burst_reset[client_ip] = now + timedelta(seconds=10)
      return False

    self.burst_tracker[client_ip] += 1
    return True

  def _check_rate_limits(self, client_ip: str, now: datetime) -> bool:
    """Check if rate limits are exceeded"""
    history = self.request_history[client_ip]

    # Check per-minute limit
    one_minute_ago = now - timedelta(minutes=1)
    recent_requests = sum(1 for req_time in history if req_time > one_minute_ago)

    if recent_requests >= self.requests_per_minute:
      return False

    # Check per-hour limit
    if len(history) >= self.requests_per_hour:
      return False

    return True


async def error_handler(_request: Request, exc: Exception):
  """
  Handle errors consistently
  Converts all exceptions to CarloError format for uniform error responses.
  """
  match exc:
    case CarloError() as e:
      # Already in CarloError format, just log and return
      logger.error(f"[{e.source}] {e.name}: {e.description}")
      error_response = e.to_response()
      return JSONResponse(
        status_code=get_status_code(e.source),
        content=error_response.model_dump(),
      )

    case RateLimitExceeded() as e:
      # Rate limit exceeded
      logger.warning(f"Rate limit exceeded: {e}")
      carlo_error = CarloError(
        description="Rate limit exceeded. Please try again later.",
        name="RATE_LIMIT_EXCEEDED",
        source="rate_limiter",
        caused_by=str(e),
      )
      return JSONResponse(
        status_code=429,
        content=carlo_error.to_response().model_dump(),
      )

    case HTTPException() as e:
      # Convert FastAPI HTTPException to CarloError format
      logger.error(f"HTTP error {e.status_code}: {e.detail}")
      carlo_error = CarloError(
        description=str(e.detail),
        name=f"HTTP_{e.status_code}",
        source="http",
      )
      return JSONResponse(
        status_code=e.status_code,
        content=carlo_error.to_response().model_dump(),
      )

    case ValueError() as e:
      # Validation errors
      logger.error(f"Validation error: {e}")
      carlo_error = CarloError(
        description=str(e),
        name="VALIDATION_ERROR",
        source="validation",
        caused_by=f"{e.__class__.__name__}: {str(e)}",
      )
      return JSONResponse(
        status_code=400,
        content=carlo_error.to_response().model_dump(),
      )

    case Exception() as e:
      # Catch-all for unexpected errors
      logger.error(f"Unhandled error: {e}", exc_info=True)

      # Get traceback for better debugging
      import traceback

      tb = traceback.format_exc()

      carlo_error = CarloError(
        description=str(e),
        name="INTERNAL_ERROR",
        source="unknown",
        caused_by=f"{e.__class__.__name__}: {str(e)}\n\nTraceback:\n{tb}",
      )
      return JSONResponse(
        status_code=500,
        content=carlo_error.to_response().model_dump(),
      )


class LoggingMiddleware:
  def __init__(self, app: ASGIApp):
    self.app = app

  async def __call__(self, scope: Scope, receive: Receive, send: Send):
    if scope["type"] != "http":
      await self.app(scope, receive, send)
      return

    # Log incoming request
    start_time = time.time()
    method = scope["method"]
    path = scope["path"]
    query_string = scope["query_string"].decode()
    client = scope.get("client", ("unknown", 0))[0]

    logger.info(
      f"Request: {method} {path}{'?' + query_string if query_string else ''} "
      f"from {client}"
    )

    # Track response status
    status_code = None

    async def send_wrapper(message):
      nonlocal status_code
      if message["type"] == "http.response.start":
        status_code = message["status"]
      await send(message)

    # Call the next app
    await self.app(scope, receive, send_wrapper)

    # Log response
    duration = time.time() - start_time
    logger.info(f"Response: {status_code} for {method} {path} (took {duration:.3f}s)")


def setup_logging_middleware(app):
  """
  Set up all middleware for the application

  Args:
    app: FastAPI application instance
  """
  # Add middleware in reverse order (last added is executed first)

  # Logging should be outermost to log all requests
  app.add_middleware(LoggingMiddleware)

  app.add_middleware(CorrelationIdMiddleware)

  logger.info("Middleware configured successfully")
