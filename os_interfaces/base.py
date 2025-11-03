"""Abstract base classes for OS-specific interfaces"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Optional


class NotificationManager(ABC):
  """Abstract base class for notification management"""

  @abstractmethod
  def create_notification(
    self, title: str, body: str, on_clicked: Optional[Callable] = None
  ) -> None:
    """Create and show a notification

    Args:
      title: Notification title
      body: Notification body text
      on_clicked: Optional callback when notification is clicked
    """
    raise NotImplementedError


class TimerManager(ABC):
  """Abstract base class for timer/alarm management"""

  @abstractmethod
  def schedule_timer(
    self, time: datetime, command: str, args: Optional[list[str]] = None
  ) -> str:
    """Schedule a timer to run a command at a specific time.

    Args:
      time: When to run the command
      command: Path to executable or command to run
      args: Optional list of command arguments

    Returns:
      Timer ID that can be used to cancel the timer
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
