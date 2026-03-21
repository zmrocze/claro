"""Android entrypoint for the `claro-notification` worker."""

import asyncio

from os_interfaces.base import OSImplementations
from notification.main import main
from os_interfaces.android import (
  AndroidManageKeys,
  AndroidNotificationManager,
  AndroidTimerManager,
)


def run() -> None:
  os_impl = OSImplementations(
    notification_manager_cls=AndroidNotificationManager,
    timer_manager_cls=AndroidTimerManager,
    manage_keys_cls=AndroidManageKeys,
  )
  asyncio.run(main(os_impl=os_impl))


if __name__ == "__main__":
  run()
