"""Abstract base classes for OS-specific interfaces"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Callable, Optional


_os_implementations: Optional["OSImplementations"] = None


@dataclass(frozen=True)
class OSImplementations:
  """Bundle of concrete OS-interface implementations.

  Platform-specific entrypoints should construct this and pass it into
  application components.
  """

  notification_manager_cls: type["NotificationManager"]
  timer_manager_cls: type["TimerManager"]
  manage_keys_cls: type["ManageKeys"]

  def notification_manager(self, *args, **kwargs) -> "NotificationManager":
    return self.notification_manager_cls(*args, **kwargs)

  def timer_manager(self, *args, **kwargs) -> "TimerManager":
    return self.timer_manager_cls(*args, **kwargs)

  def manage_keys(self, *args, **kwargs) -> "ManageKeys":
    return self.manage_keys_cls(*args, **kwargs)


def set_os_implementations(os_impl: "OSImplementations") -> None:
  global _os_implementations
  _os_implementations = os_impl


def _default_os_implementations() -> "OSImplementations":
  from os_interfaces.linux import (
    LinuxManageKeys,
    LinuxNotificationManager,
    LinuxTimerManager,
  )

  return OSImplementations(
    notification_manager_cls=LinuxNotificationManager,
    timer_manager_cls=LinuxTimerManager,
    manage_keys_cls=LinuxManageKeys,
  )


def get_os_implementations() -> "OSImplementations":
  return _os_implementations or _default_os_implementations()


@dataclass
class ScheduleTimeRange:
  """Time range with specific dates for scheduling"""

  from_time: datetime
  to_time: datetime


class ManageKeys(ABC):
  @abstractmethod
  def get_key(self, key_name: str) -> Optional[str]:
    raise NotImplementedError

  @abstractmethod
  def set_key(self, key_name: str, value: str) -> None:
    raise NotImplementedError

  @abstractmethod
  def prompt_for_key(
    self,
    key_name: str,
    *,
    description: Optional[str] = None,
    prompt_label: Optional[str] = None,
  ) -> Optional[str]:
    raise NotImplementedError


class NotificationManager(ABC):
  """Abstract base class for notification management"""

  @abstractmethod
  async def create_notification(
    self,
    title: str,
    body: str,
    on_clicked: Optional[Callable] = None,
    on_dismissed: Optional[Callable] = None,
  ) -> None:
    """Create and show a notification

    Args:
      title: Notification title
      body: Notification body text
      on_clicked: Optional callback when notification is clicked
      on_dismissed: Optional callback when notification is dismissed
    """
    raise NotImplementedError


@dataclass
class TimerConfig:
  timing: datetime | ScheduleTimeRange
  command: str
  args: list[str] = field(default_factory=list)
  name: str | None = None


class TimerManager(ABC):
  """Abstract base class for timer/alarm management"""

  @abstractmethod
  def schedule_timer(self, timer_config: TimerConfig, appconfig: Any = None) -> str:
    """Schedule a one-shot timer to run a command.

    Args:
      timer_config: Configuration with timing (time or TimeRange), command, args, and optional name
      appconfig: Optional application configuration to pass as environment variables

    Returns:
      Timer ID that can be used to cancel the timer
    """
    raise NotImplementedError

  @abstractmethod
  def schedule_daily(
    self, command: str, args: list[str], run_time: time, appconfig: Any = None
  ) -> None:
    """Schedule a daily recurring timer to run a command.

    This method is idempotent - safe to call multiple times.

    Args:
      command: Path to executable or command to run
      args: List of command arguments
      run_time: Time of day to run the command daily
      appconfig: Optional application configuration to pass as environment variables
    """
    raise NotImplementedError

  @abstractmethod
  def cancel_timer(self, timer_id: str) -> None:
    """Cancel a scheduled timer

    Args:
      timer_id: ID of the timer to cancel
    """
    raise NotImplementedError
