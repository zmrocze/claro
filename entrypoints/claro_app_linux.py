"""Linux entrypoint for the packaged Claro app (pywebview shell + backend).

This entrypoint injects Linux OS interface implementations.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from entrypoints.claro_app_core import run_pywebview_app
from os_interfaces.base import OSImplementations
from os_interfaces.linux import (
  LinuxManageKeys,
  LinuxNotificationManager,
  LinuxTimerManager,
)

# Desktop build substitutes this path via Nix; in dev it may be overridden.
FRONTEND_PATH = Path("@FRONTEND_PATH@")


def main() -> None:
  parser = argparse.ArgumentParser(description="Claro AI Assistant")
  parser.add_argument(
    "--from-notification",
    dest="deep_link",
    help="Deep link URL from notification (claro://<session-id>)",
  )
  args = parser.parse_args()

  session_id = None
  if args.deep_link:
    # Parse the deep link to extract session_id
    # Format: claro://<session-id>
    try:
      parsed = urlparse(args.deep_link)
      if parsed.scheme == "claro":
        session_id = parsed.netloc or parsed.path.lstrip("/")
        print(f"Opening Claro with session: {session_id}", file=sys.stderr)
      else:
        print(f"Warning: Invalid deep link scheme: {parsed.scheme}", file=sys.stderr)
    except Exception as e:
      print(f"Warning: Failed to parse deep link: {e}", file=sys.stderr)

  os_impl = OSImplementations(
    notification_manager_cls=LinuxNotificationManager,
    timer_manager_cls=LinuxTimerManager,
    manage_keys_cls=LinuxManageKeys,
  )
  run_pywebview_app(frontend_path=FRONTEND_PATH, os_impl=os_impl, session_id=session_id)


if __name__ == "__main__":
  main()
