"""
Middleware for request validation and rate limiting
"""

import time
import logging
import traceback

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send
from asgi_correlation_id import CorrelationIdMiddleware
from slowapi.errors import RateLimitExceeded
from backend.exceptions import AppError, get_status_code

# Rate limiting
logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware:
  def __init__(self, app: ASGIApp):
    self.app = app

  async def __call__(self, scope: Scope, receive: Receive, send: Send):
    if scope["type"] != "http":
      await self.app(scope, receive, send)
      return

    response_started = False

    async def send_wrapper(message):
      nonlocal response_started
      if message["type"] == "http.response.start":
        response_started = True  # Mark that we've started
      logger.info(f"Send!!!!!!!!!!!!!!: {message}")
      await send(message)

    try:
      await self.app(scope, receive, send_wrapper)
    except Exception as e:
      response = error_handler(e)
      if not response_started:
        await response(scope, receive, send_wrapper)
      else:
        logger.error(
          "Can't send error - response already started (error in streaming handler, doesnt concern us really)"
        )


def error_handler(exc: Exception) -> JSONResponse:
  """
  Handle errors consistently
  Converts all exceptions to AppError format for uniform error responses.
  """
  match exc:
    case AppError() as e:
      # Already in AppError format, just log and return
      logger.error(f"[{e.source}] {e.name}: {e.description}")
      error_response = e.to_response()
      return JSONResponse(
        status_code=get_status_code(e.source),
        content=error_response.model_dump(),
      )

    case RateLimitExceeded() as e:
      # Rate limit exceeded
      logger.warning(f"Rate limit exceeded: {e}")
      carlo_error = AppError(
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
      # Convert FastAPI HTTPException to AppError format
      logger.error(f"HTTP error {e.status_code}: {e.detail}")
      carlo_error = AppError(
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
      carlo_error = AppError(
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
      tb = traceback.format_exc()

      carlo_error = AppError(
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
  # Logging should be outermost to log all requests
  app.add_middleware(LoggingMiddleware)

  app.add_middleware(CorrelationIdMiddleware)

  logger.info("Middleware configured successfully")
