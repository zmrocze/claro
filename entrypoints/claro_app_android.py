"""Android entrypoint for the packaged Claro app.

Injects Android OS interfaces into the shared pywebview+backend bootstrap.
"""

from __future__ import annotations

import os
from pathlib import Path

from os_interfaces.android import setup_android_env

setup_android_env()

from entrypoints.claro_app_core import run_pywebview_app  # noqa: E402
from os_interfaces.base import OSImplementations  # noqa: E402
from os_interfaces.android import (  # noqa: E402
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
    return Path("/data/user/0/org.claro.claro/files/app/frontend/dist")


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
