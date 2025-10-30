"""Chat API endpoints"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import traceback

from backend.agent import get_agent
from backend.sessions import get_session_manager
from backend.exceptions import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
  """Chat message model"""

  content: str
  role: str = Field(default="user", pattern="^(user|assistant)$")
  timestamp: Optional[datetime] = None
  session_id: Optional[str] = Field(default=None, description="Optional session ID")
  name: Optional[str] = Field(default=None, description="Name of the speaker")


class ChatResponse(BaseModel):
  """Chat response model"""

  content: str
  role: str = "assistant"
  timestamp: datetime
  session_id: str
  requires_action: bool = False
  action_data: Optional[Dict[str, Any]] = None


class ConversationHistory(BaseModel):
  """Conversation history model"""

  messages: List[ChatMessage]
  session_id: str


@router.post("/message", response_model=ChatResponse)
async def send_message(message: ChatMessage) -> ChatResponse:
  """
  Send a message to the AI assistant and get a response
  Uses LangGraph agent with single thread per user (app_technical.md)
  """
  try:
    # Get agent (uses single thread per user)
    try:
      agent = await get_agent()
    except Exception as e:
      raise AppError.from_exception(
        e,
        name="AGENT_INITIALIZATION_ERROR",
        source="agent",
        context="Failed to initialize agent",
      )

    try:
      sessions = get_session_manager()
    except Exception as e:
      raise AppError.from_exception(
        e,
        name="SESSION_MANAGER_ERROR",
        source="backend",
        context="Failed to get session manager",
      )

    # Get or create session for UI display only
    session_id = message.session_id or sessions.default_session_id  # type: ignore
    if not session_id:
      try:
        session_id = sessions.create_session()
        # Link session to the single agent thread
        sessions.set_thread_id(session_id, agent.thread_id)  # type: ignore
      except Exception as e:
        raise AppError.from_exception(
          e,
          name="SESSION_CREATION_ERROR",
          source="backend",
          context="Failed to create new session",
        )

    # Add user message to ephemeral session storage (for UI)
    try:
      sessions.add_message(  # type: ignore
        content=message.content,
        role=message.role,
        session_id=session_id,
        name=message.name,
      )
    except Exception as e:
      raise AppError.from_exception(
        e,
        name="MESSAGE_STORAGE_ERROR",
        source="backend",
        context="Failed to store user message",
      )

    # Invoke agent (uses single thread, handles memory internally)
    try:
      response_content = await agent.ainvoke(message=message.content)
    except Exception as e:
      # Agent errors should be surfaced to user
      raise AppError.from_exception(
        e,
        name="AGENT_EXECUTION_ERROR",
        source="agent",
        context="Agent failed to process your message",
      )

    # Add assistant response to session (for UI)
    try:
      sessions.add_message(  # type: ignore
        content=response_content, role="assistant", session_id=session_id, name="Claro"
      )
    except Exception as e:
      # Log but don't fail if we can't store the response
      logger.warning(f"Failed to store assistant response: {e}")

    # Create response
    response = ChatResponse(
      content=response_content,
      role="assistant",
      timestamp=datetime.now(),
      session_id=session_id,
      requires_action=False,
    )

    logger.info(f"Processed message for session {session_id[:8]}...")
    return response

  except AppError:
    # Re-raise AppError as-is
    raise
  except Exception as e:
    # Catch any unexpected errors
    raise AppError.from_exception(
      e,
      name="UNEXPECTED_ERROR",
      source="backend",
      context=f'An unexpected error occurred while processing your message (traceback: "{traceback.format_exc()}")',
    )


@router.get("/history/{session_id}", response_model=ConversationHistory)
async def get_conversation_history(
  session_id: str, limit: int = 50
) -> ConversationHistory:
  """
  Get conversation history for a session
  """
  try:
    sessions = get_session_manager()

    # Get messages from session
    session_messages = sessions.get_messages(session_id, limit=limit)

    # Convert to ChatMessage format
    messages = [
      ChatMessage(
        content=msg.content, role=msg.role, timestamp=msg.timestamp, name=msg.name
      )
      for msg in session_messages
    ]

    return ConversationHistory(messages=messages, session_id=session_id)

  except Exception as e:
    raise AppError.from_exception(
      e,
      name="HISTORY_RETRIEVAL_ERROR",
      source="backend",
      context="Failed to retrieve conversation history",
    )


@router.delete("/history/{session_id}")
async def clear_conversation_history(session_id: str):
  """
  Clear conversation history for a session
  """
  try:
    sessions = get_session_manager()

    # Clear session messages
    success = sessions.clear_session(session_id)  # type: ignore

    if not success:
      raise AppError(
        description=f"Session {session_id} not found",
        name="SESSION_NOT_FOUND",
        source="backend",
      )

    return {"message": "History cleared", "session_id": session_id}

  except AppError:
    raise
  except Exception as e:
    raise AppError.from_exception(
      e,
      name="HISTORY_CLEAR_ERROR",
      source="backend",
      context="Failed to clear conversation history",
    )


@router.post("/session")
async def create_session() -> Dict[str, str]:
  """
  Create a new chat session
  Note: Uses single thread per user (app_technical.md)
  """
  try:
    sessions = get_session_manager()
    agent = await get_agent()

    # Create new session
    session_id = sessions.create_session()

    # Link to the single agent thread (per user)
    sessions.set_thread_id(session_id, agent.thread_id)

    logger.info(f"Created new session {session_id} with thread {agent.thread_id}")

    return {
      "session_id": session_id,
      "thread_id": agent.thread_id,
      "message": "Session created successfully",
    }

  except Exception as e:
    raise AppError.from_exception(
      e,
      name="SESSION_CREATION_ERROR",
      source="backend",
      context="Failed to create new session",
    )


@router.get("/sessions")
async def list_sessions() -> Dict[str, Any]:
  """
  List all active sessions
  """
  try:
    sessions = get_session_manager()
    all_sessions = sessions.get_all_sessions()

    return {
      "sessions": all_sessions,
      "count": len(all_sessions),
      "default_session_id": sessions.default_session_id,
    }

  except Exception as e:
    raise AppError.from_exception(
      e,
      name="SESSION_LIST_ERROR",
      source="backend",
      context="Failed to list sessions",
    )
