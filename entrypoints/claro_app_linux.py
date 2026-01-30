"""Linux entrypoint for the packaged Claro app (pywebview shell + backend).

This entrypoint injects Linux OS interface implementations.
"""

from __future__ import annotations

from pathlib import Path

from entrypoints.claro_app_core import run_pywebview_app
from os_interfaces.base import OSImplementations
from os_interfaces.linux import LinuxNotificationManager, LinuxTimerManager

# Desktop build substitutes this path via Nix; in dev it may be overridden.
FRONTEND_PATH = Path("@FRONTEND_PATH@")


def main() -> None:
  os_impl = OSImplementations(
    notification_manager_cls=LinuxNotificationManager,
    timer_manager_cls=LinuxTimerManager,
  )
  run_pywebview_app(frontend_path=FRONTEND_PATH, os_impl=os_impl)


if __name__ == "__main__":
  main()
