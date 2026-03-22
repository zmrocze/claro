"""
Notification scheduler program (Linux CLI entrypoint).

Reads notification configuration and schedules notifications for the next day
using systemd timers.
"""

import argparse
import logging
import sys
from pathlib import Path

from platformdirs import user_config_dir

from notification_schedule.core import run_scheduler
from os_interfaces.base import OSImplementations, get_os_implementations

logging.basicConfig(
  level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main(os_impl: OSImplementations | None = None) -> None:
  """Main entrypoint for the notification scheduler."""
  parser = argparse.ArgumentParser(
    description="Schedule notifications for the next day based on configuration."
  )
  parser.add_argument(
    "--config",
    type=Path,
    help="Path to notification config file (default: ~/.config/claro/notification_schedule.yaml)",
  )
  parser.add_argument(
    "--notification-command",
    type=str,
    default="claro-notification",
    help="Path to notification program (default: claro-notification)",
  )
  args = parser.parse_args()

  if os_impl is None:
    os_impl = get_os_implementations()

  config_path = args.config or (
    Path(user_config_dir("claro", ensure_exists=True)) / "notification_schedule.yaml"
  )

  try:
    run_scheduler(config_path, os_impl, args.notification_command)
  except Exception as e:
    logger.error(f"Failed to run scheduler: {e}")
    sys.exit(1)


if __name__ == "__main__":
  main()
