"""
Claro App Backend - FastAPI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
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
from os_interfaces.linux import LinuxTimerManager

# Configure logging
logging.basicConfig(
  level=logging.INFO,
  # format='%(levelname)s [%(correlation_id)s] %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Add correlation ID filter to all handlers
for handler in logging.root.handlers:
  handler.addFilter(CorrelationIdFilter(uuid_length=4))


async def _schedule_daily_notifications():
  """Schedule the notification_schedule program to run daily."""
  try:
    timer_mgr = LinuxTimerManager(app_name="claro")
    run_time = time(hour=3, minute=0)
    timer_mgr.schedule_daily(
      command="claro-notification-scheduler", args=[], run_time=run_time
    )
    logger.info("Daily notification scheduler configured")
  except Exception as e:
    logger.error(f"Failed to schedule daily notifications: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Manage application lifecycle"""
  logger.info("Starting Claro backend...")
  asyncio.create_task(_schedule_daily_notifications())
  yield
  logger.info("Shutting down Claro backend...")


# Create FastAPI app
app = FastAPI(
  title="Claro AI Assistant",
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
  ],  # Vite dev server
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
  """Health check endpoint"""
  return {"status": "healthy", "service": "claro-backend", "version": "0.1.0"}


# Static file serving for production (when frontend is bundled)
FRONTEND_DIR = os.environ.get("CARLO_FRONTEND_PATH")
if FRONTEND_DIR:
  frontend_path = Path(FRONTEND_DIR)
  if frontend_path.exists():
    logger.info(f"Serving frontend from: {FRONTEND_DIR}")

    # Mount static assets (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")

    # Catch-all route for SPA - must be last
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
      """Serve frontend files, fallback to index.html for SPA routing"""
      file_path = frontend_path / full_path

      # If file exists, serve it
      if file_path.is_file():
        # Assets with hashes can be cached indefinitely
        return FileResponse(file_path)

      # Otherwise serve index.html (SPA fallback)
      # Important: Don't cache index.html to prevent serving stale builds
      response = FileResponse(frontend_path / "index.html")
      response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
      response.headers["Pragma"] = "no-cache"
      response.headers["Expires"] = "0"
      return response
else:
  logger.warning("Frontend directory not found or not set. API-only mode.")

  @app.get("/")
  async def root():
    """Root endpoint - API only mode"""
    return {"message": "Claro AI Assistant API", "version": "0.1.0"}


if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
