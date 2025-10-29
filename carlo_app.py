"""
Carlo Desktop Application Entry Point

This script launches the Carlo AI Assistant as a desktop application using pywebview.
It starts the FastAPI backend in a background thread and creates a webview window
to display the React frontend.
"""

import webview
import threading
import uvicorn
import sys
import time
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
  level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# These paths will be substituted by Nix during build
FRONTEND_PATH = Path("@FRONTEND_PATH@")
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000


def start_backend_server():
  """Start the FastAPI backend server in the current thread"""
  try:
    logger.info(f"Starting FastAPI backend on {BACKEND_HOST}:{BACKEND_PORT}")

    # Set frontend path for backend to serve static files
    os.environ["CARLO_FRONTEND_PATH"] = str(FRONTEND_PATH)

    # Import the FastAPI app from backend.main
    from backend.main import app

    # Run uvicorn server
    uvicorn.run(
      app,
      host=BACKEND_HOST,
      port=BACKEND_PORT,
      log_level="warning",  # Reduce noise in production
      access_log=False,
    )
  except Exception as e:
    logger.error(f"Failed to start backend server: {e}", exc_info=True)
    sys.exit(1)


def create_window():
  """Create and configure the pywebview window"""
  try:
    logger.info("Creating pywebview window")

    window = webview.create_window(
      title="Carlo AI Assistant",
      url=f"http://{BACKEND_HOST}:{BACKEND_PORT}",
      width=1200,
      height=800,
      resizable=True,
      fullscreen=False,
      min_size=(800, 600),
    )

    return window
  except Exception as e:
    logger.error(f"Failed to create window: {e}", exc_info=True)
    sys.exit(1)


def main():
  """Main entry point for the Carlo desktop application"""
  logger.info("Starting Carlo AI Assistant...")

  # Verify frontend path exists
  if not FRONTEND_PATH.exists():
    logger.error(f"Frontend path does not exist: {FRONTEND_PATH}")
    sys.exit(1)

  # Start FastAPI backend in a daemon thread
  # Daemon thread will automatically terminate when main thread exits
  backend_thread = threading.Thread(
    target=start_backend_server, daemon=True, name="FastAPI-Backend"
  )
  backend_thread.start()

  # Give the backend a moment to start up
  logger.info("Waiting for backend to initialize...")
  time.sleep(2)

  # Create and start the pywebview window
  # This will block until the window is closed
  create_window()

  logger.info("Starting pywebview...")
  webview.start(debug=False)

  logger.info("Carlo AI Assistant closed")


if __name__ == "__main__":
  main()
