"""Android entrypoint for `claro-notification-scheduler`.

Schedules next-day notifications using Android AlarmManager via the injected
Android TimerManager.
"""

from os_interfaces.base import OSImplementations
from notification_schedule.main import main
from os_interfaces.android import AndroidNotificationManager, AndroidTimerManager


def run() -> None:
  os_impl = OSImplementations(
    notification_manager_cls=AndroidNotificationManager,
    timer_manager_cls=AndroidTimerManager,
  )
  main(os_impl=os_impl)


if __name__ == "__main__":
  run()
