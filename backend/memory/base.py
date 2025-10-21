"""
Abstract base class for memory providers
Allows easy swapping between different memory implementations (Zep, custom, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class MemoryProvider(ABC):
  """Abstract base class for memory providers"""

  @property
  @abstractmethod
  def current_thread_id(self) -> Optional[str]:
    """Get the current thread ID"""
    pass

  @abstractmethod
  def create_or_get_user(
    self,
    user_id: str,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> str:
    """Create a new user or get existing user"""
    pass

  @abstractmethod
  def create_thread(
    self,
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> str:
    """Create a new conversation thread"""
    pass

  @abstractmethod
  def add_message(
    self,
    content: str,
    role: str = "user",
    name: Optional[str] = None,
    thread_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> None:
    """Add a single message to the thread"""
    pass

  @abstractmethod
  def get_context(
    self, thread_id: Optional[str] = None, mode: str = "summary"
  ) -> Optional[str]:
    """Retrieve context for a thread"""
    pass

  @abstractmethod
  def create_memory_search_tools(self, user_id: str) -> Optional[List[Any]]:
    """Create memory search tools for the agent

    Args:
      user_id: User ID to create tools for

    Returns:
      List of tools or None if not supported
    """
    pass
