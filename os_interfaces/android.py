"""Android-specific implementations of OS interfaces"""

from datetime import datetime
from typing import Any, Callable, Optional

from .base import NotificationManager, PersistentStorage, TimerManager


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


class AndroidPersistentStorage(PersistentStorage):
  """Android persistent storage"""

  def __init__(self):
    # TODO: Initialize SharedPreferences via PyJNIus
    pass

  def get(self, key: str) -> Any:
    # TODO: Implement SharedPreferences retrieval
    return None

  def set(self, key: str, value: Any) -> None:
    # TODO: Implement SharedPreferences setting
    pass

  def delete(self, key: str) -> None:
    # TODO: Implement SharedPreferences deletion
    pass
