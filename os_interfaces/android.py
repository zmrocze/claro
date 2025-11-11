"""Android-specific implementations of OS interfaces"""

from datetime import time
from typing import Callable, Optional

from .base import NotificationManager, TimerConfig, TimerManager


class AndroidNotificationManager(NotificationManager):
  """Android notification manager using PyJNIus"""

  def __init__(self):
    # TODO: Initialize PyJNIus notification manager
    pass

  async def create_notification(
    self,
    title: str,
    body: str,
    on_clicked: Optional[Callable] = None,
    on_dismissed: Optional[Callable] = None,
  ) -> None:
    # TODO: Implement using PyJNIus NotificationManager
    pass


class AndroidTimerManager(TimerManager):
  """Android timer manager using AlarmManager"""

  def __init__(self):
    # TODO: Initialize PyJNIus AlarmManager
    pass

  def schedule_timer(self, timer_config: TimerConfig) -> str:
    # TODO: Implement using AlarmManager to run command
    return "android-timer-id-1"

  def schedule_daily(self, command: str, args: list[str], run_time: time) -> None:
    # TODO: Implement Android daily scheduling
    raise NotImplementedError("Android daily scheduling not yet implemented")

  def cancel_timer(self, timer_id: str) -> None:
    # TODO: Implement timer cancellation
    pass
