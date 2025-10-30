"""
Claro Desktop Application Entry Point

This script launches the Claro AI Assistant as a desktop application using pywebview.
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
from urllib.request import urlopen
from urllib.error import URLError
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
      log_level="info",  # Show all requests for debugging
      access_log=True,  # Enable access logs
    )
  except Exception as e:
    logger.error(f"Failed to start backend server: {e}", exc_info=True)
    sys.exit(1)


def create_window():
  """Create and configure the pywebview window"""
  try:
    logger.info("Creating pywebview window")

    # Add timestamp to URL to bust cache
    cache_bust = int(time.time())

    window = webview.create_window(
      title="Claro AI Assistant",
      url=f"http://{BACKEND_HOST}:{BACKEND_PORT}?v={cache_bust}",
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


def wait_for_backend(timeout=10):
  """Wait for the backend to be ready by checking the health endpoint"""
  url = f"http://{BACKEND_HOST}:{BACKEND_PORT}/health"
  start_time = time.time()

  logger.info("Waiting for backend to be ready...")
  while time.time() - start_time < timeout:
    try:
      with urlopen(url, timeout=1) as response:
        if response.status == 200:
          logger.info("Backend is ready!")
          return True
    except (URLError, OSError):
      pass
    # time.sleep(0.5)

  logger.error(f"Backend failed to start within {timeout} seconds")
  return False


def main():
  """Main entry point for the Claro desktop application"""
  logger.info("Starting Claro AI Assistant...")

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

  # Wait for backend to be ready with health check
  if not wait_for_backend():
    logger.error("Failed to start backend server")
    sys.exit(1)

  # Create and start the pywebview window
  # This will block until the window is closed
  create_window()

  logger.info("Starting pywebview...")
  webview.start(debug=True, private_mode=False, storage_path="~/.claro")

  logger.info("Claro AI Assistant closed. Exiting...")
  # Force exit to ensure daemon threads are killed
  os._exit(0)


if __name__ == "__main__":
  main()
