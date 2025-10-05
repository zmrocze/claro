"""
Carlo App Backend - FastAPI server
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import logging

from api.chat import router as chat_router
from api.notifications import router as notifications_router
from api.actions import router as actions_router
from middleware import setup_middleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

# Set up additional middleware (rate limiting, validation, etc.)
setup_middleware(app)

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
