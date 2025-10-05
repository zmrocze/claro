"""
Middleware for request validation and rate limiting
"""

import time
import logging
from typing import Dict, Optional
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

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
      return JSONResponse(
        status_code=429,
        content={
          "detail": "Too many requests in a short time. Please slow down.",
          "retry_after": "10 seconds",
        },
      )

    # Check rate limits
    if not self._check_rate_limits(client_ip, now):
      logger.warning(f"Rate limit exceeded for {client_ip}")
      return JSONResponse(
        status_code=429,
        content={
          "detail": "Rate limit exceeded. Please try again later.",
          "retry_after": "60 seconds",
        },
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


class RequestValidationMiddleware(BaseHTTPMiddleware):
  """
  Middleware for request validation and security
  """

  def __init__(
    self,
    app,
    max_content_length: int = 10 * 1024 * 1024,  # 10MB
    allowed_content_types: Optional[list] = None,
  ):
    """
    Initialize request validator

    Args:
      app: FastAPI application
      max_content_length: Maximum allowed request body size
      allowed_content_types: List of allowed content types
    """
    super().__init__(app)
    self.max_content_length = max_content_length
    self.allowed_content_types = allowed_content_types or [
      "application/json",
      "application/x-www-form-urlencoded",
      "multipart/form-data",
      "text/plain",
    ]

  async def dispatch(self, request: Request, call_next):
    """Validate the request"""

    # Skip validation for GET requests and special paths
    if request.method == "GET" or request.url.path in ["/docs", "/openapi.json"]:
      return await call_next(request)

    # Check content length
    content_length = request.headers.get("content-length")
    if content_length:
      try:
        length = int(content_length)
        if length > self.max_content_length:
          logger.warning(f"Request too large: {length} bytes")
          return JSONResponse(
            status_code=413,
            content={
              "detail": f"Request body too large. Maximum size is {self.max_content_length} bytes"
            },
          )
      except ValueError:
        return JSONResponse(
          status_code=400, content={"detail": "Invalid content-length header"}
        )

    # Check content type for POST/PUT/PATCH requests
    if request.method in ["POST", "PUT", "PATCH"]:
      content_type = request.headers.get("content-type", "").split(";")[0].strip()

      if content_type and not any(
        allowed in content_type for allowed in self.allowed_content_types
      ):
        logger.warning(f"Invalid content type: {content_type}")
        return JSONResponse(
          status_code=415,
          content={"detail": f"Unsupported content type: {content_type}"},
        )

    # Process request
    try:
      response = await call_next(request)
      return response
    except Exception as e:
      logger.error(f"Error processing request: {e}")
      raise


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
  """
  Middleware for consistent error handling
  """

  async def dispatch(self, request: Request, call_next):
    """Handle errors consistently"""
    try:
      response = await call_next(request)
      return response

    except HTTPException:
      # Let FastAPI handle HTTP exceptions
      raise

    except ValueError as e:
      logger.error(f"Validation error: {e}")
      return JSONResponse(
        status_code=400, content={"detail": str(e), "type": "validation_error"}
      )

    except Exception as e:
      logger.error(f"Unhandled error: {e}", exc_info=True)

      # Don't expose internal errors in production
      return JSONResponse(
        status_code=500,
        content={
          "detail": "An internal error occurred. Please try again later.",
          "type": "internal_error",
        },
      )


class LoggingMiddleware(BaseHTTPMiddleware):
  """
  Middleware for request/response logging
  """

  async def dispatch(self, request: Request, call_next):
    """Log requests and responses"""
    start_time = time.time()

    # Log request
    logger.info(
      f"Request: {request.method} {request.url.path} "
      f"from {request.client.host if request.client else 'unknown'}"
    )

    try:
      response = await call_next(request)

      # Log response
      duration = time.time() - start_time
      logger.info(
        f"Response: {response.status_code} for {request.method} {request.url.path} "
        f"(took {duration:.3f}s)"
      )

      # Add custom headers
      response.headers["X-Process-Time"] = str(duration)
      response.headers["X-Carlo-Version"] = "0.1.0"

      return response

    except Exception as e:
      duration = time.time() - start_time
      logger.error(
        f"Error processing {request.method} {request.url.path} "
        f"after {duration:.3f}s: {e}"
      )
      raise


def setup_middleware(app):
  """
  Set up all middleware for the application

  Args:
    app: FastAPI application instance
  """
  # Add middleware in reverse order (last added is executed first)

  # Logging should be outermost to log all requests
  app.add_middleware(LoggingMiddleware)

  # Error handling
  app.add_middleware(ErrorHandlingMiddleware)

  # Request validation
  app.add_middleware(
    RequestValidationMiddleware,
    max_content_length=10 * 1024 * 1024,  # 10MB
  )

  # Rate limiting
  app.add_middleware(
    RateLimitMiddleware, requests_per_minute=120, requests_per_hour=2000, burst_size=20
  )

  logger.info("Middleware configured successfully")
