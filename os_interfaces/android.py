"""Android-specific implementations of OS interfaces"""

from datetime import datetime
from typing import Callable, Optional

from .base import NotificationManager, TimerManager


class AndroidNotificationManager(NotificationManager):
  """Android notification manager using PyJNIus"""

  def __init__(self):
    # TODO: Initialize PyJNIus notification manager
    pass

  def create_notification(
    self, title: str, body: str, on_clicked: Optional[Callable] = None
  ) -> None:
    # TODO: Implement using PyJNIus NotificationManager
    pass


class AndroidTimerManager(TimerManager):
  """Android timer manager using AlarmManager"""

  def __init__(self):
    # TODO: Initialize PyJNIus AlarmManager
    pass

  def schedule_timer(
    self, time: datetime, command: str, args: Optional[list[str]] = None
  ) -> str:
    # TODO: Implement using AlarmManager to run command
    return "android-timer-id-1"

  def cancel_timer(self, timer_id: str) -> None:
    # TODO: Implement timer cancellation
    pass
