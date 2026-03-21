"""Android entrypoint for the packaged Claro app.

Injects Android OS interfaces into the shared pywebview+backend bootstrap.
"""

from __future__ import annotations

import os
from pathlib import Path

# Set up environment file path before any imports that use config
try:
  from android.storage import app_storage_path  # type: ignore

  env_file = Path(app_storage_path()) / "app" / "builds" / "android" / ".env.android"
except Exception:
  env_file = Path("/data/user/0/org.claro/files/app/builds/android/.env.android")

if env_file.exists():
  os.environ["CLARO_DOTENV_PATH"] = str(env_file)

from entrypoints.claro_app_core import run_pywebview_app
from os_interfaces.base import OSImplementations
from os_interfaces.android import (
  AndroidManageKeys,
  AndroidNotificationManager,
  AndroidTimerManager,
)


def _frontend_path() -> Path:
  env_path = os.environ.get("CARLO_FRONTEND_PATH")
  if env_path:
    return Path(env_path)
  try:
    from android.storage import app_storage_path  # type: ignore

    return Path(app_storage_path()) / "app" / "frontend" / "dist"
  except Exception:
    return Path("/data/user/0/org.claro/files/app/frontend/dist")


FRONTEND_PATH = _frontend_path()


def main() -> None:
  os_impl = OSImplementations(
    notification_manager_cls=AndroidNotificationManager,
    timer_manager_cls=AndroidTimerManager,
    manage_keys_cls=AndroidManageKeys,
  )
  run_pywebview_app(frontend_path=FRONTEND_PATH, os_impl=os_impl)


if __name__ == "__main__":
  main()
