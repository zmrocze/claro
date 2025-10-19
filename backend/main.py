"""
Carlo App Backend - FastAPI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging
from asgi_correlation_id import CorrelationIdFilter

from backend.api.chat import router as chat_router
from backend.api.notifications import router as notifications_router
from backend.api.actions import router as actions_router
from backend.middleware import error_handler, setup_logging_middleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

# Configure logging
logging.basicConfig(
  level=logging.INFO,
  # format='%(levelname)s [%(correlation_id)s] %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# Add correlation ID filter to all handlers
for handler in logging.root.handlers:
  handler.addFilter(CorrelationIdFilter(uuid_length=4))


@asynccontextmanager
async def lifespan(app: FastAPI):
  """Manage application lifecycle"""
  logger.info("Starting Carlo backend...")
  # Initialize resources here (Zep, API clients, etc.)
  yield
  # Cleanup
  logger.info("Shutting down Carlo backend...")


# Create FastAPI app
app = FastAPI(
  title="Carlo AI Assistant",
  description="Personal AI assistant with chat interface and notifications",
  version="0.1.0",
  lifespan=lifespan,
)

limiter = Limiter(key_func=get_remote_address, default_limits=["3600/hour"])
app.state.limiter = limiter

app.add_exception_handler(Exception, error_handler)

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

app.add_middleware(SlowAPIMiddleware)

# Set up additional middleware (rate limiting, validation, etc.)
setup_logging_middleware(app)

# Include routers
app.include_router(chat_router)
app.include_router(notifications_router)
app.include_router(actions_router)


@app.get("/")
async def root():
  """Root endpoint"""
  return {"message": "Carlo AI Assistant API", "version": "0.1.0"}


@app.get("/health")
async def health_check():
  """Health check endpoint"""
  return {"status": "healthy", "service": "carlo-backend", "version": "0.1.0"}


if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
