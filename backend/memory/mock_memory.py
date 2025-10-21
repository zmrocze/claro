"""
Mock memory provider for testing and development
"""

import uuid
from typing import Optional, Dict, Any, List

from backend.memory.base import MemoryProvider


class MockMemoryProvider(MemoryProvider):
  """Mock memory provider for testing purposes"""

  def __init__(self):
    self._current_thread_id: Optional[str] = None
    self._current_user_id: Optional[str] = None
    self._users: Dict[str, Dict[str, Any]] = {}
    self._threads: Dict[str, Dict[str, Any]] = {}
    self._messages: Dict[str, List[Dict[str, Any]]] = {}

  @property
  def current_thread_id(self) -> Optional[str]:
    """Get the current thread ID"""
    return self._current_thread_id

  def create_or_get_user(
    self,
    user_id: str,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> str:
    """Create a new user or get existing user"""
    if user_id not in self._users:
      self._users[user_id] = {
        "user_id": user_id,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "metadata": metadata or {},
      }
    self._current_user_id = user_id
    return user_id

  def create_thread(
    self,
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> str:
    """Create a new conversation thread"""
    if thread_id is None:
      thread_id = uuid.uuid4().hex

    user_id = user_id or self._current_user_id
    if not user_id:
      raise ValueError("User ID is required to create a thread")

    self._threads[thread_id] = {
      "thread_id": thread_id,
      "user_id": user_id,
      "metadata": metadata or {},
    }
    self._messages[thread_id] = []
    self._current_thread_id = thread_id
    return thread_id

  def add_message(
    self,
    content: str,
    role: str = "user",
    name: Optional[str] = None,
    thread_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> None:
    """Add a single message to the thread"""
    thread_id = thread_id or self.current_thread_id
    if not thread_id:
      raise ValueError("Thread ID is required to add messages")

    if thread_id not in self._messages:
      self._messages[thread_id] = []

    message = {
      "content": content,
      "role": role,
      "name": name,
      "metadata": metadata or {},
    }
    self._messages[thread_id].append(message)

  def get_context(
    self, thread_id: Optional[str] = None, mode: str = "summary"
  ) -> Optional[str]:
    """Retrieve context for a thread"""
    thread_id = thread_id or self.current_thread_id
    if not thread_id or thread_id not in self._messages:
      return None

    messages = self._messages[thread_id]
    if not messages:
      return None

    # Simple context generation for testing
    context_parts = []
    for msg in messages[-5:]:  # Last 5 messages
      context_parts.append(f"{msg['role']}: {msg['content']}")

    return "Previous conversation:\n" + "\n".join(context_parts)

  def create_memory_search_tools(self, user_id: str) -> Optional[List[Any]]:
    """Create memory search tools for the agent

    Args:
      user_id: User ID to create tools for

    Returns:
      None - mock provider doesn't support search tools
    """
    return None
