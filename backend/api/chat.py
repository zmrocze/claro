"""Chat API endpoints"""

import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
import logging

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


class ConversationHistory(BaseModel):
  """Conversation history model"""

  messages: List[ChatMessage]
  session_id: str


class StreamEvent(BaseModel):
  """SSE event data model"""

  event: str  # "start", "token", "done", "error"
  data: Dict[str, Any]


async def _stream_response(
  message: ChatMessage,
) -> AsyncGenerator[str, None]:
  """
  Generator that streams SSE events for a chat message.
  Yields SSE-formatted strings.
  """
  session_id = None
  accumulated_content = ""
  try:
    # Get agent and session manager
    agent = await get_agent()
    sessions = get_session_manager()

    # Get or create session
    session_id = message.session_id or sessions.default_session_id
    if not session_id:
      session_id = sessions.create_session()
      sessions.set_thread_id(session_id, agent.thread_id)

    # Send start event
    yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"

    # Add user message to session storage
    try:
      sessions.add_message(
        content=message.content,
        role=message.role,
        session_id=session_id,
        name=message.name,
      )
    except Exception as e:
      logger.warning(f"Failed to store user message: {e}")

    # Stream tokens from agent
    async for chunk in agent.astream_tokens(message=message.content):
      if chunk["type"] == "token":
        accumulated_content += chunk["content"]
        yield f"event: token\ndata: {json.dumps({'content': chunk['content']})}\n\n"
      elif chunk["type"] == "done":
        # Store final response in session
        try:
          sessions.add_message(
            content=accumulated_content,
            role="assistant",
            session_id=session_id,
            name="Claro",
          )
        except Exception as e:
          logger.warning(f"Failed to store assistant response: {e}")

        yield f"event: done\ndata: {json.dumps({'content': accumulated_content, 'session_id': session_id})}\n\n"

  except Exception as e:
    logger.error(f"Error in stream_response: {e}")
    # Extract clean error info for frontend
    if isinstance(e, AppError):
      error_msg = e.description
      error_code = e.name
    else:
      # Generic exception - extract just the message, not headers/details
      error_msg = str(e).split("\n")[0][:200]  # First line, max 200 chars
      error_code = type(e).__name__
    error_data = {
      "error": error_msg,
      "code": error_code,
      "partial_content": accumulated_content,
    }
    yield f"event: error\ndata: {json.dumps(error_data)}\n\n"


@router.post("/message")
async def send_message(message: ChatMessage) -> StreamingResponse:
  """
  Send a message to the AI assistant and stream the response.
  Uses Server-Sent Events (SSE) for real-time token streaming.

  Events:
  - start: {"session_id": "..."} - Stream started
  - token: {"content": "..."} - LLM token chunk
  - done: {"content": "...", "session_id": "..."} - Complete response
  - error: {"error": "...", "code": "...", "partial_content": "..."} - Error occurred
  """
  return StreamingResponse(
    _stream_response(message),
    media_type="text/event-stream",
    headers={
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",  # Disable nginx buffering
    },
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
