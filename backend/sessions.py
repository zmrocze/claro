"""
Session management for ephemeral conversation history
Handles in-memory storage of recent messages
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from threading import Lock
from collections import deque

from pydantic import BaseModel

from backend.config import AppConfig

logger = logging.getLogger(__name__)


class SessionMessage(BaseModel):
  """Message in a session"""

  content: str
  role: str  # 'user' or 'assistant'
  timestamp: datetime
  name: Optional[str] = None
  metadata: Optional[Dict[str, Any]] = None


class Session:
  """Represents a conversation session with ephemeral history"""

  def __init__(self, session_id: str, max_messages: int = 500):
    """
    Initialize a session

    Args:
      session_id: Unique session identifier
      max_messages: Maximum number of messages to keep
    """
    self.session_id = session_id
    self.created_at = datetime.now()
    self.last_activity = datetime.now()
    self.max_messages = max_messages

    # Use deque for efficient message management with max size
    self.messages: deque[SessionMessage] = deque(maxlen=max_messages)

    # Thread ID for Zep integration
    self.thread_id: Optional[str] = None

    # User info
    self.user_id: Optional[str] = None

    # Session metadata
    self.metadata: Dict[str, Any] = {}

  def add_message(self, message: SessionMessage) -> None:
    """Add a message to the session"""
    self.messages.append(message)
    self.last_activity = datetime.now()

  def get_messages(self, limit: Optional[int] = None) -> List[SessionMessage]:
    """Get messages from the session"""
    if limit:
      return list(self.messages)[-limit:]
    return list(self.messages)

  def clear_messages(self) -> None:
    """Clear all messages from the session"""
    self.messages.clear()
    self.last_activity = datetime.now()

  def is_expired(self, timeout_hours: int = 24) -> bool:
    """Check if session has expired"""
    expiry_time = self.last_activity + timedelta(hours=timeout_hours)
    return datetime.now() > expiry_time

  def to_dict(self) -> Dict[str, Any]:
    """Convert session to dictionary"""
    return {
      "session_id": self.session_id,
      "created_at": self.created_at.isoformat(),
      "last_activity": self.last_activity.isoformat(),
      "message_count": len(self.messages),
      "thread_id": self.thread_id,
      "user_id": self.user_id,
      "metadata": self.metadata,
    }


class SessionManager:
  """Manages multiple conversation sessions"""

  def __init__(self):
    """Initialize the session manager"""
    self.sessions: Dict[str, Session] = {}
    self.lock = Lock()
    self.max_messages = AppConfig.MAX_SESSION_MESSAGES
    self.timeout_hours = AppConfig.SESSION_TIMEOUT_HOURS

    # Default session ID for single-user app instance
    self.default_session_id: Optional[str] = None

  def create_session(
    self,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    thread_id: Optional[str] = None,
  ) -> str:
    """
    Create a new session

    Args:
      session_id: Optional session ID (will generate if not provided)
      user_id: Optional user ID
      thread_id: Optional Zep thread ID

    Returns:
      The session ID
    """
    with self.lock:
      session_id = session_id or uuid.uuid4().hex

      if session_id in self.sessions:
        logger.warning(f"Session {session_id} already exists, returning existing")
        return session_id

      session = Session(session_id, self.max_messages)
      session.user_id = user_id
      session.thread_id = thread_id

      self.sessions[session_id] = session

      # Set as default if first session
      if not self.default_session_id:
        self.default_session_id = session_id

      logger.info(f"Created session {session_id}")
      return session_id

  def get_session(self, session_id: Optional[str] = None) -> Optional[Session]:
    """
    Get a session by ID

    Args:
      session_id: Session ID (uses default if not provided)

    Returns:
      Session object or None if not found
    """
    session_id = session_id or self.default_session_id

    if not session_id:
      return None

    with self.lock:
      return self.sessions.get(session_id)

  def add_message(
    self,
    content: str,
    role: str,
    session_id: Optional[str] = None,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
  ) -> None:
    """
    Add a message to a session

    Args:
      content: Message content
      role: Message role (user/assistant)
      session_id: Session ID (uses default if not provided)
      name: Optional speaker name
      metadata: Optional message metadata
    """
    session = self.get_session(session_id)

    if not session:
      # Auto-create session if it doesn't exist
      session_id = self.create_session(session_id)
      session = self.get_session(session_id)

    message = SessionMessage(
      content=content, role=role, timestamp=datetime.now(), name=name, metadata=metadata
    )

    with self.lock:
      session.add_message(message)  # type: ignore[reportOptionalAttributeAccess]

    logger.debug(f"Added message to session {session.session_id}")  # type: ignore[reportOptionalAttributeAccess]

  def get_messages(
    self, session_id: Optional[str] = None, limit: Optional[int] = None
  ) -> List[SessionMessage]:
    """
    Get messages from a session

    Args:
      session_id: Session ID (uses default if not provided)
      limit: Maximum number of messages to return

    Returns:
      List of messages
    """
    session = self.get_session(session_id)

    if not session:
      return []

    with self.lock:
      return session.get_messages(limit)

  def clear_session(self, session_id: Optional[str] = None) -> bool:
    """
    Clear messages from a session

    Args:
      session_id: Session ID (uses default if not provided)

    Returns:
      True if cleared, False if session not found
    """
    session = self.get_session(session_id)

    if not session:
      return False

    with self.lock:
      session.clear_messages()

    logger.info(f"Cleared session {session.session_id}")
    return True

  def delete_session(self, session_id: str) -> bool:
    """
    Delete a session

    Args:
      session_id: Session ID to delete

    Returns:
      True if deleted, False if not found
    """
    with self.lock:
      if session_id in self.sessions:
        del self.sessions[session_id]

        # Update default if needed
        if session_id == self.default_session_id:
          self.default_session_id = None
          if self.sessions:
            self.default_session_id = next(iter(self.sessions.keys()))

        logger.info(f"Deleted session {session_id}")
        return True

    return False

  def cleanup_expired_sessions(self) -> int:
    """
    Remove expired sessions

    Returns:
      Number of sessions removed
    """
    with self.lock:
      expired = [
        sid
        for sid, session in self.sessions.items()
        if session.is_expired(self.timeout_hours)
      ]

      for sid in expired:
        del self.sessions[sid]
        if sid == self.default_session_id:
          self.default_session_id = None
          if self.sessions:
            self.default_session_id = next(iter(self.sessions.keys()))

      if expired:
        logger.info(f"Cleaned up {len(expired)} expired sessions")

      return len(expired)

  def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
    """
    Get information about all sessions

    Returns:
      Dictionary of session info
    """
    with self.lock:
      return {sid: session.to_dict() for sid, session in self.sessions.items()}

  def set_thread_id(self, session_id: str, thread_id: str) -> bool:
    """
    Set the Zep thread ID for a session

    Args:
      session_id: Session ID
      thread_id: Zep thread ID

    Returns:
      True if set, False if session not found
    """
    session = self.get_session(session_id)

    if not session:
      return False

    with self.lock:
      session.thread_id = thread_id

    return True

  def get_thread_id(self, session_id: Optional[str] = None) -> Optional[str]:
    """
    Get the Zep thread ID for a session

    Args:
      session_id: Session ID (uses default if not provided)

    Returns:
      Thread ID or None
    """
    session = self.get_session(session_id)

    if not session:
      return None

    return session.thread_id


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
  """
  Get or create the singleton session manager

  Returns:
    SessionManager instance
  """
  global _session_manager

  if _session_manager is None:
    _session_manager = SessionManager()

  return _session_manager
