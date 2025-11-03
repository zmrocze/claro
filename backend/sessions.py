"""
Session management with persistent storage
Handles conversation history with disk persistence
"""

import json
import logging
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from platformdirs import user_data_dir
from pydantic import BaseModel, Field

from backend.config import AppConfig

logger = logging.getLogger(__name__)


class SessionMessage(BaseModel):
  """Message in a session"""

  message_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
  content: str
  role: str  # 'user' or 'assistant'
  timestamp: datetime
  name: Optional[str] = None
  metadata: Optional[Dict[str, Any]] = None

  def to_file_dict(self) -> Dict[str, Any]:
    """Convert to dictionary for file storage"""
    return {
      "message_id": self.message_id,
      "content": self.content,
      "role": self.role,
      "timestamp": self.timestamp.isoformat(),
      "name": self.name,
      "metadata": self.metadata,
    }

  @classmethod
  def from_file_dict(cls, data: Dict[str, Any]) -> "SessionMessage":
    """Create from file dictionary"""
    return cls(
      message_id=data["message_id"],
      content=data["content"],
      role=data["role"],
      timestamp=datetime.fromisoformat(data["timestamp"]),
      name=data.get("name"),
      metadata=data.get("metadata"),
    )


class SessionPersistence:
  """Handles disk storage for a single session"""

  def __init__(self, session_id: str, storage_dir: Path):
    """
    Initialize session persistence

    Args:
      session_id: Unique session identifier
      storage_dir: Base directory for all sessions
    """
    self.session_id = session_id
    self.session_dir = storage_dir / session_id
    self.executor = ThreadPoolExecutor(
      max_workers=2, thread_name_prefix="session-persist"
    )

  def _get_message_filename(self, message: SessionMessage) -> str:
    """Generate filename for a message"""
    # Use timestamp (ms) + message_id for unique, sortable filenames
    timestamp_ms = int(message.timestamp.timestamp() * 1000)
    return f"{timestamp_ms}_{message.message_id}.json"

  def save_message_async(self, message: SessionMessage) -> None:
    """
    Save message to disk asynchronously (fire-and-forget)

    Args:
      message: Message to save
    """
    self.executor.submit(self._save_message_sync, message)

  def _save_message_sync(self, message: SessionMessage) -> None:
    """Synchronous message save (runs in thread pool)"""
    try:
      self.session_dir.mkdir(parents=True, exist_ok=True)
      filename = self._get_message_filename(message)
      filepath = self.session_dir / filename

      with open(filepath, "w") as f:
        json.dump(message.to_file_dict(), f, indent=2)

      logger.debug(f"Saved message {message.message_id} to {filepath}")
    except Exception as e:
      logger.error(f"Failed to save message {message.message_id}: {e}")

  def load_all_messages(self) -> List[SessionMessage]:
    """
    Load all messages from disk, sorted by timestamp

    Returns:
      List of messages sorted by timestamp (oldest first)
    """
    if not self.session_dir.exists():
      return []

    messages = []
    try:
      for filepath in self.session_dir.glob("*.json"):
        try:
          with open(filepath, "r") as f:
            data = json.load(f)
          message = SessionMessage.from_file_dict(data)
          messages.append(message)
        except Exception as e:
          logger.warning(f"Failed to load message from {filepath}: {e}")

      # Sort by timestamp (filename already encodes this, but be explicit)
      messages.sort(key=lambda m: m.timestamp)
      logger.debug(f"Loaded {len(messages)} messages for session {self.session_id}")
      return messages

    except Exception as e:
      logger.error(f"Failed to load messages for session {self.session_id}: {e}")
      return []

  def cleanup_old_messages(self, max_age_hours: int, max_count: int) -> int:
    """
    Delete old message files based on age and count limits

    Args:
      max_age_hours: Maximum age of messages in hours
      max_count: Maximum number of messages to keep

    Returns:
      Number of messages deleted
    """
    if not self.session_dir.exists():
      return 0

    try:
      # Get all message files with their timestamps
      message_files = []
      for filepath in self.session_dir.glob("*.json"):
        try:
          with open(filepath, "r") as f:
            data = json.load(f)
          timestamp = datetime.fromisoformat(data["timestamp"])
          message_files.append((filepath, timestamp))
        except Exception as e:
          logger.warning(f"Failed to read timestamp from {filepath}: {e}")

      if not message_files:
        return 0

      # Sort by timestamp (oldest first)
      message_files.sort(key=lambda x: x[1])

      deleted_count = 0
      cutoff_date = datetime.now() - timedelta(hours=max_age_hours)

      # Delete old messages
      for filepath, timestamp in message_files:
        # Delete if too old
        if timestamp < cutoff_date:
          filepath.unlink()
          deleted_count += 1
          logger.debug(f"Deleted old message: {filepath}")

      # Delete excess messages (keep only max_count most recent)
      remaining_files = [
        (fp, ts)
        for fp, ts in message_files
        if (fp, ts) not in message_files[:deleted_count]
      ]
      if len(remaining_files) > max_count:
        excess_count = len(remaining_files) - max_count
        for filepath, _ in remaining_files[:excess_count]:
          filepath.unlink()
          deleted_count += 1
          logger.debug(f"Deleted excess message: {filepath}")

      if deleted_count > 0:
        logger.info(
          f"Cleaned up {deleted_count} messages for session {self.session_id}"
        )

      return deleted_count

    except Exception as e:
      logger.error(f"Failed to cleanup messages for session {self.session_id}: {e}")
      return 0

  def clear_all_messages(self) -> None:
    """Delete all message files and the session directory"""
    if not self.session_dir.exists():
      return

    try:
      # Delete all message files
      for filepath in self.session_dir.glob("*.json"):
        filepath.unlink()

      # Remove the empty session directory
      self.session_dir.rmdir()
      logger.info(
        f"Cleared all messages and removed directory for session {self.session_id}"
      )
    except Exception as e:
      logger.error(f"Failed to clear messages for session {self.session_id}: {e}")


class Session:
  """Represents a conversation session with persistent storage"""

  def __init__(
    self, session_id: str, persistence: SessionPersistence, max_messages: int = 500
  ):
    """
    Initialize a session

    Args:
      session_id: Unique session identifier
      persistence: SessionPersistence instance for disk I/O
      max_messages: Maximum number of messages to keep in memory
    """
    self.session_id = session_id
    self.persistence = persistence
    self.created_at = datetime.now()
    self.last_activity = datetime.now()
    self.max_messages = max_messages

    # Lazy loading flag
    self._loaded = False

    # Use deque for efficient message management with max size
    self.messages: deque[SessionMessage] = deque(maxlen=max_messages)

    # Thread ID for Zep integration
    self.thread_id: Optional[str] = None

    # User info
    self.user_id: Optional[str] = None

    # Session metadata
    self.metadata: Dict[str, Any] = {}

  def _ensure_loaded(self) -> None:
    """Lazy load messages from disk on first access"""
    if self._loaded:
      return

    # Load all messages from disk
    messages = self.persistence.load_all_messages()

    # Apply cleanup rules
    max_age = AppConfig.MAX_MESSAGE_AGE_HOURS
    max_count = AppConfig.MAX_SESSION_MESSAGES

    # Filter by age
    cutoff_date = datetime.now() - timedelta(hours=max_age)
    messages = [m for m in messages if m.timestamp >= cutoff_date]

    # Keep only most recent max_count messages
    if len(messages) > max_count:
      messages = messages[-max_count:]

    # Populate deque
    self.messages.extend(messages)

    # Clean up disk to match memory state
    self.persistence.cleanup_old_messages(max_age, max_count)

    self._loaded = True
    logger.info(f"Loaded {len(messages)} messages for session {self.session_id}")

  def add_message(self, message: SessionMessage) -> None:
    """
    Add a message to the session

    Args:
      message: Message to add
    """
    # Ensure loaded before adding
    self._ensure_loaded()

    # Add to memory
    self.messages.append(message)
    self.last_activity = datetime.now()

    # Save to disk asynchronously
    self.persistence.save_message_async(message)

  def get_messages(self, limit: Optional[int] = None) -> List[SessionMessage]:
    """
    Get messages from the session

    Args:
      limit: Maximum number of recent messages to return

    Returns:
      List of messages (most recent if limit specified)
    """
    # Ensure loaded before returning
    self._ensure_loaded()

    if limit:
      return list(self.messages)[-limit:]
    return list(self.messages)

  def clear_messages(self) -> None:
    """Clear all messages from the session"""
    self.messages.clear()
    self.last_activity = datetime.now()

    # Clear disk storage
    self.persistence.clear_all_messages()

  def is_expired(self, timeout_hours: int = 24) -> bool:
    """Check if session has expired"""
    expiry_time = self.last_activity + timedelta(hours=timeout_hours)
    return datetime.now() > expiry_time

  def to_dict(self) -> Dict[str, Any]:
    """Convert session to dictionary"""
    # Ensure loaded to get accurate count
    self._ensure_loaded()

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
  """Manages multiple conversation sessions with persistent storage"""

  def __init__(self):
    """Initialize the session manager"""
    self.sessions: Dict[str, Session] = {}
    self.lock = Lock()
    self.max_messages = AppConfig.MAX_SESSION_MESSAGES
    self.timeout_hours = AppConfig.SESSION_TIMEOUT_HOURS

    # Storage directory for all sessions
    self.storage_dir = Path(user_data_dir("carlo", ensure_exists=True)) / "sessions"
    self.storage_dir.mkdir(parents=True, exist_ok=True)

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

      # Create persistence handler
      persistence = SessionPersistence(session_id, self.storage_dir)

      # Create session with persistence
      session = Session(session_id, persistence, self.max_messages)
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
    Get a session by ID, restoring from disk if needed

    Args:
      session_id: Session ID (uses default if not provided)

    Returns:
      Session object or None if not found
    """
    session_id = session_id or self.default_session_id

    if not session_id:
      return None

    with self.lock:
      # Check if session exists in memory
      if session_id in self.sessions:
        return self.sessions[session_id]

      # Session not in memory - check if it exists on disk
      session_dir = self.storage_dir / session_id
      if session_dir.exists() and session_dir.is_dir():
        # Restore session from disk
        logger.info(f"Restoring session {session_id} from disk")
        persistence = SessionPersistence(session_id, self.storage_dir)
        session = Session(session_id, persistence, self.max_messages)
        self.sessions[session_id] = session

        # Set as default if we don't have one
        if not self.default_session_id:
          self.default_session_id = session_id

        return session

      # Session doesn't exist in memory or on disk
      return None

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

    # Session.add_message handles both memory and disk
    session.add_message(message)  # type: ignore

    logger.debug(f"Added message to session {session.session_id}")  # type: ignore

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
        session = self.sessions[session_id]

        # Clear disk storage
        session.clear_messages()

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
        session = self.sessions[sid]

        # Clear disk storage
        session.clear_messages()

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
