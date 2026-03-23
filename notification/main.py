"""
Send system notifications using named prompts from a YAML config (Linux CLI).

Usage:
    uv run python -m notification.main <notification_name>
"""

import argparse
import asyncio
import logging
import subprocess
from pathlib import Path

from platformdirs import user_config_dir

from notification.core import fire_notification
from os_interfaces.base import OSImplementations, get_os_implementations

logging.basicConfig(
  level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _open_app_on_click(session_id: str) -> None:
  try:
    subprocess.Popen(
      ["xdg-open", f"claro://{session_id}"],
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
    )
  except Exception as e:
    logger.error(f"Failed to open app: {e}")


async def main(os_impl: OSImplementations | None = None) -> None:
  parser = argparse.ArgumentParser(
    description="Send a system notification using a named prompt from the notification schedule config."
  )
  parser.add_argument(
    "notification-name",
    help="Name of the notification to trigger (must exist in notification_schedule.yaml)",
  )
  args = parser.parse_args()

  if os_impl is None:
    os_impl = get_os_implementations()

  config_path = (
    Path(user_config_dir("claro", ensure_exists=True)) / "notification_schedule.yaml"
  )

  done_event = asyncio.Event()

  session_id = await fire_notification(
    notification_name=getattr(args, "notification-name"),
    config_path=config_path,
    os_impl=os_impl,
    on_clicked=lambda: (_open_app_on_click(session_id), done_event.set()),
    on_dismissed=done_event.set,
  )

  logger.info("Waiting for notification interaction...")
  await done_event.wait()
  logger.info("Notification interaction complete, exiting")


if __name__ == "__main__":
  asyncio.run(main())
