"""Chat API endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import traceback

from backend.agent import get_agent
from backend.sessions import get_session_manager
from zep_cloud.client import AsyncZep
from backend.config import get_zep_api_key, AppConfig

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
  context_used: bool = Field(
    default=False, description="Whether context from memory was used"
  )


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
    agent = await get_agent()
    sessions = get_session_manager()

    # Get or create session for UI display only
    session_id = message.session_id or sessions.default_session_id  # type: ignore
    if not session_id:
      session_id = sessions.create_session()
      # Link session to the single agent thread
      sessions.set_thread_id(session_id, agent.thread_id)  # type: ignore

    # Add user message to ephemeral session storage (for UI)
    sessions.add_message(  # type: ignore
      content=message.content,
      role=message.role,
      session_id=session_id,
      name=message.name,
    )

    # Invoke agent (uses single thread, handles memory internally)
    try:
      response_content = await agent.ainvoke(message=message.content)
      context_used = True  # Agent always uses memory context
    except Exception as e:
      logger.error(f"Agent error: {e}")
      response_content = "I apologize, but I'm having trouble processing your request right now. Please try again."
      context_used = False

    # Add assistant response to session (for UI)
    sessions.add_message(  # type: ignore
      content=response_content, role="assistant", session_id=session_id, name="Carlo"
    )

    # Create response
    response = ChatResponse(
      content=response_content,
      role="assistant",
      timestamp=datetime.now(),
      session_id=session_id,
      requires_action=False,
      context_used=context_used,
    )

    logger.info(f"Processed message for session {session_id[:8]}...")
    return response

  except Exception as e:
    logger.error(f"Error processing message: {e}\n{traceback.format_exc()}")
    raise HTTPException(
      status_code=500,
      detail=f"An error occurred while processing your message: {str(e)}",
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
    logger.error(f"Error retrieving history: {e}")
    raise HTTPException(status_code=500, detail=str(e))


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
      raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    return {"message": "History cleared", "session_id": session_id}

  except HTTPException:
    raise
  except Exception as e:
    logger.error(f"Error clearing history: {e}")
    raise HTTPException(status_code=500, detail=str(e))


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
    logger.error(f"Error creating session: {e}")
    raise HTTPException(status_code=500, detail=str(e))


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
    logger.error(f"Error listing sessions: {e}")
    raise HTTPException(status_code=500, detail=str(e))
