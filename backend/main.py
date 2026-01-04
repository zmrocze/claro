"""
Claro App Backend - FastAPI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import os
import asyncio
from datetime import time
from pathlib import Path
from asgi_correlation_id import CorrelationIdFilter

from backend.api.chat import router as chat_router
from backend.api.notifications import router as notifications_router
from backend.api.actions import router as actions_router
from backend.middleware import ErrorHandlingMiddleware, setup_logging_middleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from os_interfaces.base import OSImplementations
from os_interfaces.linux import LinuxTimerManager

# Configure logging
logging.basicConfig(
  # todo: config
  level=logging.INFO,
  # format='%(levelname)s [%(correlation_id)s] %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Add correlation ID filter to all handlers
for handler in logging.root.handlers:
  handler.addFilter(CorrelationIdFilter(uuid_length=4))


async def _schedule_daily_notifications(os_impl: OSImplementations):
  """Schedule the notification_schedule program to run daily."""
  try:
    timer_mgr = os_impl.timer_manager(app_name="claro")
    run_time = time(hour=3, minute=0)
    timer_mgr.schedule_daily(
      command="claro-notification-scheduler", args=[], run_time=run_time
    )
    logger.info("Daily notification scheduler configured")
  except Exception as e:
    logger.error(f"Failed to schedule daily notifications: {e}")


def create_app(*, os_impl: OSImplementations | None = None) -> FastAPI:
  """Create the FastAPI application.

  `os_impl` allows platform-specific entrypoints to inject Android vs Linux
  timer/notification implementations.
  """

  if os_impl is None:
    # Default to Linux for local development / existing behavior.
    os_impl = OSImplementations(
      notification_manager_cls=lambda *a, **k: None,  # type: ignore[arg-type]
      timer_manager_cls=LinuxTimerManager,
    )

  @asynccontextmanager
  async def lifespan(app: FastAPI):
    logger.info("Starting Claro backend...")
    asyncio.create_task(_schedule_daily_notifications(os_impl))
    yield
    logger.info("Shutting down Claro backend...")

  app = FastAPI(
    title="Claro",
    description="Personal AI assistant with chat interface and notifications",
    version="0.1.0",
    lifespan=lifespan,
    exception_handlers={},
  )

  # innermost
  app.add_middleware(ErrorHandlingMiddleware)

  # Configure CORS for frontend
  app.add_middleware(
    CORSMiddleware,
    allow_origins=[
      "http://localhost:5173",
      "http://localhost:5174",
      "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )

  limiter = Limiter(key_func=get_remote_address, default_limits=["3600/hour"])
  app.state.limiter = limiter

  app.add_middleware(SlowAPIMiddleware)

  # outermost
  setup_logging_middleware(app)

  # Include routers
  app.include_router(chat_router)
  app.include_router(notifications_router)
  app.include_router(actions_router)

  @app.get("/health")
  async def health_check():
    return {"status": "healthy", "service": "claro-backend", "version": "0.1.0"}

  # Static file serving for production (when frontend is bundled)
  FRONTEND_DIR = os.environ.get("CARLO_FRONTEND_PATH")
  if FRONTEND_DIR:
    frontend_path = Path(FRONTEND_DIR)
    if frontend_path.exists():
      logger.info(f"Serving frontend from: {FRONTEND_DIR}")

      app.mount(
        "/assets", StaticFiles(directory=frontend_path / "assets"), name="assets"
      )

      @app.get("/{full_path:path}")
      async def serve_frontend(full_path: str):
        """Serve frontend files, fallback to index.html for SPA routing"""
        index_path = frontend_path / "index.html"
        file_path = frontend_path / full_path
        if file_path.exists() and file_path.is_file():
          return FileResponse(file_path)
        return FileResponse(index_path)

  else:
    logger.warning("Frontend directory not found or not set. API-only mode.")

    @app.get("/")
    async def root():
      return {"message": "Claro AI Assistant API", "version": "0.1.0"}

  return app


# Backwards-compatible default import path (existing code imports `app`)
app = create_app(
  os_impl=OSImplementations(
    notification_manager_cls=lambda *a, **k: None,  # type: ignore[arg-type]
    timer_manager_cls=LinuxTimerManager,
  )
)
