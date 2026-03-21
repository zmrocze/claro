"""Linux entrypoint for `claro-notification-scheduler`."""

from os_interfaces.base import OSImplementations
from notification_schedule.main import main
from os_interfaces.linux import (
  LinuxManageKeys,
  LinuxNotificationManager,
  LinuxTimerManager,
)


def run() -> None:
  os_impl = OSImplementations(
    notification_manager_cls=LinuxNotificationManager,
    timer_manager_cls=LinuxTimerManager,
    manage_keys_cls=LinuxManageKeys,
  )
  main(os_impl=os_impl)


if __name__ == "__main__":
  run()
