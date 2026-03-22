"""p4a foreground service: individual notification runner.

Triggered by AlarmManager at a scheduled time. Receives notification name
via PYTHON_SERVICE_ARGUMENT, calls the LLM agent, and shows a notification.
"""

from os_interfaces.android import setup_android_env

setup_android_env()

import asyncio  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402

from notification.core import fire_notification  # noqa: E402
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
  notification_name = os.environ.get("PYTHON_SERVICE_ARGUMENT", "")
  logger.info("Notifier service started for '%s'", notification_name)
  if not notification_name:
    logger.error("No notification name provided, stopping")
    return

  os_impl = OSImplementations(
    notification_manager_cls=AndroidNotificationManager,
    timer_manager_cls=AndroidTimerManager,
    manage_keys_cls=AndroidManageKeys,
  )
  try:
    asyncio.run(fire_notification(notification_name, _android_config_path(), os_impl))
  except Exception:
    logger.exception("Notifier service failed")
  finally:
    from jnius import autoclass  # type: ignore

    autoclass("org.kivy.android.PythonService").mService.stopSelf()
    logger.info("Notifier service stopped")


if __name__ == "__main__":
  main()
