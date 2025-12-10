"""
Notification scheduler program.

Reads notification configuration and schedules notifications for the next day
using systemd timers.
"""

import argparse
import logging
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from platformdirs import user_config_dir

from notification_schedule.config_parser import (
  NotificationConfig,
  TimeRange,
  parse_notification_config,
)
from os_interfaces.base import ScheduleTimeRange, TimerConfig
from os_interfaces.linux import LinuxTimerManager

logging.basicConfig(
  level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def schedule_notification(
  timer_mgr: LinuxTimerManager,
  notification_name: str,
  config: NotificationConfig,
  notification_command: str,
) -> None:
  """Schedule a single notification based on its configuration.

  Handles frequency:
  - frequency < 1: probabilistic scheduling (draw random to decide if schedule)
  - frequency >= 1: schedule floor(frequency) or ceil(frequency) times based on fractional part
    e.g., 1.5 means 50% chance of 1 schedule, 50% chance of 2 schedules

  Args:
      timer_mgr: Timer manager instance
      notification_name: Name of the notification
      config: Notification configuration
      notification_command: Path to the notification program
  """
  frequency = config.frequency

  # Determine number of schedules based on frequency
  # floor(frequency) + (1 if random < fractional_part else 0)
  # Works for all cases: 0.8 -> 0 or 1, 1.5 -> 1 or 2, 2.3 -> 2 or 3
  base = int(frequency)
  fractional = frequency - base
  num_schedules = base + (1 if random.random() < fractional else 0)

  if num_schedules == 0:
    logger.info(
      f"Skipping '{notification_name}' (frequency={frequency}, random draw failed)"
    )
    return

  for i in range(num_schedules):
    # Generate unique name for multiple schedules
    timer_name = f"{notification_name}-{i}" if num_schedules > 1 else notification_name

    # Convert time to datetime for tomorrow
    tomorrow = (datetime.now() + timedelta(days=1)).date()
    if isinstance(config.timing, TimeRange):
      # Convert TimeRange to ScheduleTimeRange with tomorrow's date
      adjusted_timing = ScheduleTimeRange(
        from_time=datetime.combine(tomorrow, config.timing.from_time),
        to_time=datetime.combine(tomorrow, config.timing.to_time),
      )
    else:
      # Convert time to datetime with tomorrow's date
      adjusted_timing = datetime.combine(tomorrow, config.timing)

    timer_config = TimerConfig(
      timing=adjusted_timing,
      command=notification_command,
      args=[notification_name],
      name=timer_name,
    )

    try:
      timer_id = timer_mgr.schedule_timer(timer_config)
      timing_str = (
        f"{config.timing.from_time}-{config.timing.to_time}"
        if isinstance(config.timing, TimeRange)
        else str(config.timing)
      )
      logger.info(
        f"Scheduled notification '{timer_name}' at {timing_str} with timer ID: {timer_id}"
      )
    except Exception as e:
      logger.error(f"Failed to schedule notification '{timer_name}': {e}")


def main() -> None:
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
    default="notify-with-carlo",
    help="Path to notification program (default: notify-with-carlo)",
  )
  args = parser.parse_args()

  # Determine config path
  config_path = args.config or (
    Path(user_config_dir("claro", ensure_exists=True)) / "notification_schedule.yaml"
  )

  # Load configuration
  try:
    schedule_config = parse_notification_config(config_path)
    logger.info(f"Loaded configuration from {config_path}")
  except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    sys.exit(1)

  # Initialize timer manager
  timer_mgr = LinuxTimerManager(app_name="claro")

  # Schedule each notification
  for notification_name, notification_config in schedule_config.notifications.items():
    logger.info(f"Processing notification: {notification_name}")
    schedule_notification(
      timer_mgr, notification_name, notification_config, args.notification_command
    )

  logger.info("Notification scheduling complete")


if __name__ == "__main__":
  main()
