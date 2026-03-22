"""p4a foreground service: daily notification scheduler.

Triggered by AlarmManager at 3 AM. Reads notification config and schedules
individual notification alarms via AndroidTimerManager.
"""

from os_interfaces.android import setup_android_env

setup_android_env()

import logging  # noqa: E402

from notification_schedule.core import run_scheduler  # noqa: E402
from os_interfaces.android import _android_config_path  # noqa: E402
from os_interfaces.base import OSImplementations  # noqa: E402
from os_interfaces.android import (  # noqa: E402
  AndroidManageKeys,
  AndroidNotificationManager,
  AndroidTimerManager,
)

logging.basicConfig(
  level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
  logger.info("Scheduler service started")
  os_impl = OSImplementations(
    notification_manager_cls=AndroidNotificationManager,
    timer_manager_cls=AndroidTimerManager,
    manage_keys_cls=AndroidManageKeys,
  )
  try:
    run_scheduler(_android_config_path(), os_impl)
  except Exception:
    logger.exception("Scheduler service failed")
  finally:
    from jnius import autoclass  # type: ignore

    autoclass("org.kivy.android.PythonService").mService.stopSelf()
    logger.info("Scheduler service stopped")


if __name__ == "__main__":
  main()
