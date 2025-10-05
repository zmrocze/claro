"""Chat API endpoints"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import traceback

from backend.memory import get_memory_client
from backend.sessions import get_session_manager
from backend.llm import get_llm_manager
# from zep_cloud.types import Message as ZepMessage

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
  """
  try:
    # Get managers
    memory = get_memory_client()
    sessions = get_session_manager()
    llm = get_llm_manager()

    # Get or create session
    session_id = message.session_id or sessions.default_session_id  # type: ignore
    if not session_id:
      session_id = sessions.create_session()

    # Get thread ID from session or create new one
    thread_id = sessions.get_thread_id(session_id)  # type: ignore
    if not thread_id:
      # Create new thread if needed
      if not memory.current_thread_id:
        thread_id = memory.create_thread()
      else:
        thread_id = memory.current_thread_id
      sessions.set_thread_id(session_id, thread_id)  # type: ignore

    # Add message to ephemeral session storage
    sessions.add_message(  # type: ignore
      content=message.content,
      role=message.role,
      session_id=session_id,
      name=message.name,
    )

    # Add message to Zep memory
    try:
      memory.add_message(
        content=message.content,
        role=message.role,
        name=message.name or "User",
        thread_id=thread_id,
      )
    except Exception as e:
      logger.warning(f"Failed to add message to Zep: {e}")

    # Get context from Zep
    context = None
    context_used = False
    try:
      context = memory.get_context(thread_id=thread_id, mode="basic")
      context_used = context is not None
    except Exception as e:
      logger.warning(f"Failed to get context from Zep: {e}")

    # Get recent chat history from session
    recent_messages = sessions.get_messages(session_id, limit=10)  # type: ignore
    chat_history = [
      {"role": msg.role, "content": msg.content}
      for msg in recent_messages[:-1]  # Exclude the current message
    ]

    # Get response from LLM
    try:
      response_content = await llm.get_response_async(
        message=message.content, context=context, chat_history=chat_history
      )
    except Exception as e:
      logger.error(f"LLM error: {e}")
      response_content = "I apologize, but I'm having trouble processing your request right now. Please try again."

    # Add assistant response to session
    sessions.add_message(  # type: ignore
      content=response_content, role="assistant", session_id=session_id, name="Carlo"
    )

    # Add assistant response to Zep
    try:
      memory.add_message(
        content=response_content, role="assistant", name="Carlo", thread_id=thread_id
      )
    except Exception as e:
      logger.warning(f"Failed to add assistant response to Zep: {e}")

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
  """
  try:
    sessions = get_session_manager()
    memory = get_memory_client()

    # Create new session
    session_id = sessions.create_session()

    # Create new Zep thread for this session
    thread_id = memory.create_thread()
    sessions.set_thread_id(session_id, thread_id)

    logger.info(f"Created new session {session_id} with thread {thread_id}")

    return {
      "session_id": session_id,
      "thread_id": thread_id,
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
