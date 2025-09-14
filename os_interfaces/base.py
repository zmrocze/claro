"""Abstract base classes for OS-specific interfaces"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Optional


class NotificationManager(ABC):
  """Abstract base class for notification management"""

  @abstractmethod
  def create_notification(self, title: str, body: str, data: dict) -> None:
    """Create and show a notification"""
    raise NotImplementedError

  @abstractmethod
  def cancel_notification(self, notification_id: str) -> None:
    """Cancel a scheduled notification"""
    raise NotImplementedError


class TimerManager(ABC):
  """Abstract base class for timer/alarm management"""

  @abstractmethod
  def schedule_timer(
    self, time: datetime, callback: Callable, data: Optional[dict] = None
  ) -> str:
    """Schedule a timer to trigger at a specific time. Returns timer id."""
    raise NotImplementedError

  @abstractmethod
  def cancel_timer(self, timer_id: str) -> None:
    """Cancel a scheduled timer"""
    raise NotImplementedError


class PersistentStorage(ABC):
  """Abstract base class for persistent storage"""

  @abstractmethod
  def get(self, key: str) -> Any:
    """Retrieve a value from persistent storage"""
    raise NotImplementedError

  @abstractmethod
  def set(self, key: str, value: Any) -> None:
    """Store a value in persistent storage"""
    raise NotImplementedError

  @abstractmethod
  def delete(self, key: str) -> None:
    """Delete a value from persistent storage"""
    raise NotImplementedError
