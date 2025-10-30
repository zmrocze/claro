"""
Zep memory management for Claro App
Handles conversation memory storage and retrieval
"""

import logging
import uuid
from typing import Optional, List, Dict, Any

from zep_cloud import Zep
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message


from backend.config import AppConfig, get_zep_api_key
from backend.memory.base import MemoryProvider
from backend.agent.tools import create_zep_tools

logger = logging.getLogger(__name__)


class ZepMemory(MemoryProvider):
  """Manages conversation memory using Zep"""

  def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
    """
    Initialize Zep memory client

    Args:
      api_key: Optional API key (will use config if not provided)
      api_url: Optional API URL (will use config if not provided)
    """
    self.api_key = api_key or get_zep_api_key()
    self.api_url = api_url or AppConfig.ZEP_API_URL

    # Initialize Zep client
    try:
      if self.api_key:
        ## TODO:THIS fails, probably, probably api_key is None
        self.client = Zep(api_key=self.api_key, base_url=self.api_url)
      else:
        # For local Zep without authentication
        self.client = Zep(base_url=self.api_url)

      logger.info(f"Zep client initialized with URL: {self.api_url}")
    except Exception as e:
      logger.error(f"Failed to initialize Zep client: {e}")
      raise

    # Store active user and thread IDs
    self.current_user_id: Optional[str] = None
    self._current_thread_id: Optional[str] = None

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
    """
    Create a new user or get existing user

    Args:
      user_id: Unique user identifier
      email: User's email address
      first_name: User's first name
      last_name: User's last name
      metadata: Additional user metadata

    Returns:
      The user ID
    """
    try:
      # Try to get existing user first
      try:
        _user = self.client.user.get(user_id)
        logger.info(f"Retrieved existing user: {user_id}")
        self.current_user_id = user_id
        return user_id
      except Exception as e:
        if "not found" in str(e).lower():
          # User doesn't exist, create new one
          pass
        else:
          raise

      # Create new user
      self.client.user.add(
        user_id=user_id,
        email=email,
        first_name=first_name or "Claro",
        last_name=last_name or "User",
      )
      logger.info(f"Created new user: {user_id}")
      self.current_user_id = user_id
      return user_id

    except Exception as e:
      logger.error(f"Failed to create/get user {user_id}: {e}")
      raise

  def create_thread(
    self,
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> str:
    """
    Create a new conversation thread

    Args:
      thread_id: Optional thread ID (will generate if not provided)
      user_id: User ID for the thread (uses current if not provided)
      metadata: Additional thread metadata

    Returns:
      The thread ID
    """
    try:
      thread_id = thread_id or uuid.uuid4().hex
      user_id = user_id or self.current_user_id

      if not user_id:
        raise ValueError("User ID is required to create a thread")

      self.client.thread.create(thread_id=thread_id, user_id=user_id)
      logger.info(f"Created thread {thread_id} for user {user_id}")
      self._current_thread_id = thread_id
      return thread_id

    except Exception as e:
      logger.error(f"Failed to create thread: {e}")
      raise

  def add_message(
    self,
    content: str,
    role: str = "user",
    name: Optional[str] = None,
    thread_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> None:
    """
    Add a single message to the thread

    Args:
      content: Message content
      role: Message role (user/assistant)
      name: Name of the speaker
      thread_id: Thread ID (uses current if not provided)
      metadata: Additional message metadata
    """
    thread_id = thread_id or self.current_thread_id

    if not thread_id:
      raise ValueError("Thread ID is required to add messages")

    message = Message(content=content, role=role, name=name)

    self.add_messages([message], thread_id)

  def add_messages(
    self, messages: List[Message], thread_id: Optional[str] = None
  ) -> None:
    """
    Add multiple messages to a thread

    Args:
      messages: List of Message objects
      thread_id: Thread ID (uses current if not provided)
    """
    try:
      thread_id = thread_id or self.current_thread_id

      if not thread_id:
        raise ValueError("Thread ID is required to add messages")

      self.client.thread.add_messages(thread_id, messages=messages)
      logger.debug(f"Added {len(messages)} messages to thread {thread_id}")

    except Exception as e:
      logger.error(f"Failed to add messages to thread {thread_id}: {e}")
      raise

  def get_context(
    self, thread_id: Optional[str] = None, mode: str = "summary"
  ) -> Optional[str]:
    """
    Retrieve context for a thread

    Args:
      thread_id: Thread ID (uses current if not provided)
      mode: Context mode ('summary' or 'basic')

    Returns:
      Context string for use in prompts
    """
    try:
      thread_id = thread_id or self.current_thread_id

      if not thread_id:
        raise ValueError("Thread ID is required to get context")

      memory = self.client.thread.get_user_context(thread_id=thread_id, mode=mode)

      if memory and memory.context:
        logger.debug(f"Retrieved context for thread {thread_id}")
        return memory.context

      return None

    except Exception as e:
      logger.error(f"Failed to get context for thread {thread_id}: {e}")
      return None

  def get_thread_messages(
    self, thread_id: Optional[str] = None, limit: int = 50
  ) -> List[Message]:
    """
    Get messages from a thread

    Args:
      thread_id: Thread ID (uses current if not provided)
      limit: Maximum number of messages to retrieve

    Returns:
      List of messages
    """
    try:
      thread_id = thread_id or self.current_thread_id

      if not thread_id:
        raise ValueError("Thread ID is required to get messages")

      result = self.client.thread.get(thread_id)

      if result and result.messages:
        messages = result.messages[:limit]
        logger.debug(f"Retrieved {len(messages)} messages from thread {thread_id}")
        return messages

      return []

    except Exception as e:
      logger.error(f"Failed to get messages from thread {thread_id}: {e}")
      return []

  def search_memories(
    self, query: str, user_id: Optional[str] = None, limit: int = 10
  ) -> List[Dict[str, Any]]:
    """
    Search user memories

    Args:
      query: Search query
      user_id: User ID (uses current if not provided)
      limit: Maximum number of results

    Returns:
      List of memory search results
    """
    try:
      user_id = user_id or self.current_user_id

      if not user_id:
        raise ValueError("User ID is required to search memories")

      # Search using graph search if available
      results = self.client.graph.search(
        user_id=user_id,
        query=query,
        limit=limit,
        scope="edges",
      )

      if not results or not results.edges:
        return []

      logger.debug(f"Found {len(results.edges)} memory results for query: {query}")

      # Convert edges to a list of dicts
      return [edge.model_dump() for edge in results.edges]

    except Exception as e:
      logger.error(f"Failed to search memories: {e}")
      return []

  def add_business_data(
    self, data: str, data_type: str = "text", user_id: Optional[str] = None
  ) -> None:
    """
    Add business data to user's graph

    Args:
      data: Data to add (text or JSON string)
      data_type: Type of data ('text' or 'json')
      user_id: User ID (uses current if not provided)
    """
    try:
      user_id = user_id or self.current_user_id

      if not user_id:
        raise ValueError("User ID is required to add business data")

      self.client.graph.add(user_id=user_id, type=data_type, data=data)

      logger.info(f"Added {data_type} data to user {user_id}'s graph")

    except Exception as e:
      logger.error(f"Failed to add business data: {e}")
      raise

  def delete_thread(self, thread_id: Optional[str] = None) -> None:
    """
    Delete a thread

    Args:
      thread_id: Thread ID to delete (uses current if not provided)
    """
    try:
      thread_id = thread_id or self.current_thread_id

      if not thread_id:
        raise ValueError("Thread ID is required to delete thread")

      self.client.thread.delete(thread_id)
      logger.info(f"Deleted thread {thread_id}")

      if thread_id == self.current_thread_id:
        self._current_thread_id = None

    except Exception as e:
      logger.error(f"Failed to delete thread {thread_id}: {e}")
      raise

  def create_memory_search_tools(self, user_id: str) -> Optional[List[Any]]:
    """Create memory search tools for the agent

    Args:
      user_id: User ID to create tools for

    Returns:
      List of Zep search tools
    """
    # Create AsyncZep client for tools
    try:
      if self.api_key:
        async_client = AsyncZep(api_key=self.api_key, base_url=self.api_url)
      else:
        async_client = AsyncZep(base_url=self.api_url)

      return create_zep_tools(async_client, user_id)
    except Exception as e:
      logger.error(f"Failed to create memory search tools: {e}")
      return None


# Singleton instance
_memory_client: Optional[ZepMemory] = None


def get_memory_client() -> ZepMemory:
  """
  Get or create the singleton Zep memory client

  Returns:
    ZepMemory instance
  """
  global _memory_client

  if _memory_client is None:
    _memory_client = ZepMemory()

  return _memory_client


def initialize_memory() -> None:
  """Initialize the memory system with a default user and thread"""
  try:
    memory = get_memory_client()

    # Create default user for the app instance
    user_id = f"carlo_user_{uuid.uuid4().hex[:8]}"
    memory.create_or_get_user(user_id=user_id, first_name="Claro", last_name="User")

    # Create initial thread
    memory.create_thread()

    logger.info(
      f"Memory system initialized with user {user_id} and thread {memory.current_thread_id}"
    )

  except Exception as e:
    logger.error(f"Failed to initialize memory system: {e}")
    raise
