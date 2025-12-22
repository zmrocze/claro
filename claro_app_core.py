"""Platform-agnostic pywebview app bootstrap.

The platform-specific entrypoints (Linux/Android) should import this module and
provide the correct OS-interface implementations.

Contract:
- Inputs: an os-interface bundle `os_impl` with at least `timer_manager()`.
- Behavior: starts the FastAPI backend (configured with the os interfaces) + opens a webview.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import uvicorn
import webview

from os_interfaces.base import OSImplementations

WEBVIEW_DEBUG = os.getenv("CLARO_WEBVIEW_DEBUG", "").strip().lower() in {"1", "true"}

logging.basicConfig(
  level=logging.DEBUG if WEBVIEW_DEBUG else logging.INFO,
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000


def _start_backend_server(frontend_path: Path, os_impl: OSImplementations) -> None:
  try:
    logger.info("Starting FastAPI backend on %s:%s", BACKEND_HOST, BACKEND_PORT)
    os.environ["CARLO_FRONTEND_PATH"] = str(frontend_path)

    from backend.main import create_app

    app = create_app(os_impl=os_impl)

    uvicorn.run(
      app,
      host=BACKEND_HOST,
      port=BACKEND_PORT,
      log_level="info",
      access_log=True,
    )
  except Exception:
    logger.exception("Failed to start backend server")
    sys.exit(1)


def _wait_for_backend(timeout: int = 10) -> bool:
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

  logger.error("Backend failed to start within %s seconds", timeout)
  return False


def _create_window() -> None:
  cache_bust = int(time.time())
  webview.create_window(
    title="Claro AI Assistant",
    url=f"http://{BACKEND_HOST}:{BACKEND_PORT}?v={cache_bust}",
    width=1200,
    height=800,
    resizable=True,
    fullscreen=False,
    min_size=(800, 600),
  )


def run_pywebview_app(*, frontend_path: Path, os_impl: OSImplementations) -> None:
  logger.info("Starting Claro UI shell...")

  if not frontend_path.exists():
    raise FileNotFoundError(f"Frontend path does not exist: {frontend_path}")

  backend_thread = threading.Thread(
    target=_start_backend_server,
    args=(frontend_path, os_impl),
    daemon=True,
    name="FastAPI-Backend",
  )
  backend_thread.start()

  if not _wait_for_backend():
    raise RuntimeError("Backend failed to start")

  _create_window()

  logger.info("Starting pywebview...")
  webview.start(debug=WEBVIEW_DEBUG, private_mode=False, storage_path="~/.claro")

  logger.info("Claro window closed. Exiting...")
  os._exit(0)
