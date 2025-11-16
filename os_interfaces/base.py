"""Abstract base classes for OS-specific interfaces"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import time
from typing import Any, Callable, Optional

from notification_schedule.config_parser import TimeRange


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
  timing: TimeRange | time
  command: str
  args: list[str] = field(default_factory=list)
  name: str | None = None


class TimerManager(ABC):
  """Abstract base class for timer/alarm management"""

  @abstractmethod
  def schedule_timer(self, timer_config: TimerConfig) -> str:
    """Schedule a one-shot timer to run a command.

    Args:
      timer_config: Configuration with timing (time or TimeRange), command, args, and optional name

    Returns:
      Timer ID that can be used to cancel the timer
    """
    raise NotImplementedError

  @abstractmethod
  def schedule_daily(self, command: str, args: list[str], run_time: time) -> None:
    """Schedule a daily recurring timer to run a command.

    This method is idempotent - safe to call multiple times.

    Args:
      command: Path to executable or command to run
      args: List of command arguments
      run_time: Time of day to run the command daily
    """
    raise NotImplementedError

  @abstractmethod
  def cancel_timer(self, timer_id: str) -> None:
    """Cancel a scheduled timer

    Args:
      timer_id: ID of the timer to cancel
    """
    raise NotImplementedError


class ConfigStorage(ABC):
  """Abstract base class for configuration file storage"""

  @abstractmethod
  def load(self) -> dict:
    """Load configuration from storage"""
    raise NotImplementedError

  @abstractmethod
  def save(self, config: dict) -> None:
    """Save configuration to storage"""
    raise NotImplementedError

  @abstractmethod
  def get(self, key: str, default: Any = None) -> Any:
    """Get a configuration value by key"""
    raise NotImplementedError

  @abstractmethod
  def set(self, key: str, value: Any) -> None:
    """Set a configuration value"""
    raise NotImplementedError
