"""Android entrypoint for the packaged Claro app.

Injects Android OS interfaces into the shared pywebview+backend bootstrap.
"""

from __future__ import annotations

import os
from pathlib import Path

from entrypoints.claro_app_core import run_pywebview_app
from os_interfaces.base import OSImplementations
from os_interfaces.android import AndroidNotificationManager, AndroidTimerManager

# On Android we rely on runtime-provided assets; in practice this may be set via env.
FRONTEND_PATH = Path(
  os.environ.get("CARLO_FRONTEND_PATH", "/data/user/0/org.claro/files/frontend")
)


def main() -> None:
  os_impl = OSImplementations(
    notification_manager_cls=AndroidNotificationManager,
    timer_manager_cls=AndroidTimerManager,
  )
  run_pywebview_app(frontend_path=FRONTEND_PATH, os_impl=os_impl)


if __name__ == "__main__":
  main()
