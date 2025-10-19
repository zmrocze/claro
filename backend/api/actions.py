"""
Actions API endpoints
Handles action execution with user confirmation
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum
import logging
import uuid

from backend.exceptions import CarloError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/actions", tags=["actions"])


class ActionType(str, Enum):
  """Available action types"""

  MOCK = "mock"
  REMINDER = "reminder"
  NOTE = "note"
  SEARCH = "search"


class ActionRequest(BaseModel):
  """Request to execute an action"""

  action_type: ActionType
  parameters: Dict[str, Any] = Field(default_factory=dict)
  description: str = Field(..., description="Human-readable description of the action")
  requires_confirmation: bool = Field(
    default=True, description="Whether user confirmation is required"
  )
  session_id: Optional[str] = None


class ActionConfirmation(BaseModel):
  """Action confirmation request"""

  action_id: str
  action_type: ActionType
  description: str
  parameters: Dict[str, Any]
  created_at: datetime
  expires_at: datetime


class ActionResult(BaseModel):
  """Result of an action execution"""

  action_id: str
  action_type: ActionType
  status: str  # "pending", "confirmed", "executed", "failed", "cancelled"
  result: Optional[Dict[str, Any]] = None
  error: Optional[str] = None
  executed_at: Optional[datetime] = None


# In-memory storage for pending actions (should be persistent in production)
_pending_actions: Dict[str, ActionConfirmation] = {}
_action_results: Dict[str, ActionResult] = {}


class ActionHandler:
  """Base class for action handlers"""

  @staticmethod
  async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the action with given parameters"""
    raise NotImplementedError


class MockActionHandler(ActionHandler):
  """Mock action handler for testing"""

  @staticmethod
  async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute mock action"""
    logger.info(f"Executing mock action with parameters: {parameters}")

    # Simulate some work
    import asyncio

    await asyncio.sleep(0.5)

    return {
      "message": "Mock action executed successfully",
      "parameters_received": parameters,
      "timestamp": datetime.now().isoformat(),
    }


class ReminderActionHandler(ActionHandler):
  """Handler for setting reminders"""

  @staticmethod
  async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute reminder action"""
    time = parameters.get("time")
    message = parameters.get("message", "Reminder")

    logger.info(f"Setting reminder: {message} at {time}")

    # In production, this would integrate with the notification system
    return {
      "reminder_set": True,
      "time": time,
      "message": message,
      "reminder_id": str(uuid.uuid4()),
    }


class NoteActionHandler(ActionHandler):
  """Handler for saving notes"""

  @staticmethod
  async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute note action"""
    content = parameters.get("content", "")
    title = parameters.get("title", "Untitled Note")

    logger.info(f"Saving note: {title}")

    # In production, this would save to persistent storage
    return {
      "note_saved": True,
      "title": title,
      "content_length": len(content),
      "note_id": str(uuid.uuid4()),
    }


class SearchActionHandler(ActionHandler):
  """Handler for search actions"""

  @staticmethod
  async def execute(parameters: Dict[str, Any]) -> Dict[str, Any]:
    """Execute search action"""
    query = parameters.get("query", "")
    scope = parameters.get("scope", "all")

    logger.info(f"Searching for: {query} in scope: {scope}")

    # Mock search results
    return {
      "query": query,
      "scope": scope,
      "results_count": 5,
      "results": [
        {"title": f"Result {i + 1}", "snippet": f"Sample result for '{query}'"}
        for i in range(5)
      ],
    }


# Action handler registry
ACTION_HANDLERS = {
  ActionType.MOCK: MockActionHandler,
  ActionType.REMINDER: ReminderActionHandler,
  ActionType.NOTE: NoteActionHandler,
  ActionType.SEARCH: SearchActionHandler,
}


@router.post("/execute", response_model=ActionResult)
async def execute_action(request: ActionRequest) -> ActionResult:
  """
  Request execution of an action
  """
  try:
    action_id = str(uuid.uuid4())

    # If confirmation required, create pending action
    if request.requires_confirmation:
      confirmation = ActionConfirmation(
        action_id=action_id,
        action_type=request.action_type,
        description=request.description,
        parameters=request.parameters,
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=5),
      )

      _pending_actions[action_id] = confirmation

      result = ActionResult(
        action_id=action_id,
        action_type=request.action_type,
        status="pending",
        result={"confirmation_required": True, "expires_in_seconds": 300},
      )

      _action_results[action_id] = result

      logger.info(f"Action {action_id} pending confirmation")
      return result

    # Execute immediately if no confirmation required
    handler = ACTION_HANDLERS.get(request.action_type)
    if not handler:
      raise ValueError(f"Unknown action type: {request.action_type}")

    try:
      execution_result = await handler.execute(request.parameters)

      result = ActionResult(
        action_id=action_id,
        action_type=request.action_type,
        status="executed",
        result=execution_result,
        executed_at=datetime.now(),
      )

      _action_results[action_id] = result

      logger.info(f"Action {action_id} executed successfully")
      return result

    except Exception as e:
      result = ActionResult(
        action_id=action_id,
        action_type=request.action_type,
        status="failed",
        error=str(e),
      )

      _action_results[action_id] = result

      logger.error(f"Action {action_id} failed: {e}")
      return result

  except Exception as e:
    logger.error(f"Error processing action request: {e}")
    raise CarloError.from_exception(
      e,
      name="ACTION_REQUEST_ERROR",
      source="actions",
      context="Failed to process action request",
    )


@router.get("/pending", response_model=List[ActionConfirmation])
async def get_pending_actions() -> List[ActionConfirmation]:
  """
  Get list of actions pending confirmation
  """
  try:
    # Remove expired actions
    now = datetime.now()
    expired = [
      aid for aid, action in _pending_actions.items() if action.expires_at < now
    ]

    for aid in expired:
      del _pending_actions[aid]
      if aid in _action_results:
        _action_results[aid].status = "expired"

    return list(_pending_actions.values())

  except Exception as e:
    logger.error(f"Error getting pending actions: {e}")
    raise CarloError.from_exception(
      e,
      name="PENDING_ACTIONS_ERROR",
      source="actions",
      context="Failed to retrieve pending actions",
    )


@router.post("/confirm/{action_id}", response_model=ActionResult)
async def confirm_action(action_id: str) -> ActionResult:
  """
  Confirm and execute a pending action
  """
  try:
    if action_id not in _pending_actions:
      raise CarloError(
        description=f"Action {action_id} not found or has expired",
        name="ACTION_NOT_FOUND",
        source="actions",
      )

    action = _pending_actions[action_id]

    # Check if expired
    if action.expires_at < datetime.now():
      del _pending_actions[action_id]
      _action_results[action_id].status = "expired"
      raise CarloError(
        description="Action has expired and can no longer be confirmed",
        name="ACTION_EXPIRED",
        source="actions",
      )

    # Execute the action
    handler = ACTION_HANDLERS.get(action.action_type)
    if not handler:
      raise ValueError(f"Unknown action type: {action.action_type}")

    try:
      execution_result = await handler.execute(action.parameters)

      result = ActionResult(
        action_id=action_id,
        action_type=action.action_type,
        status="executed",
        result=execution_result,
        executed_at=datetime.now(),
      )

      # Clean up pending action
      del _pending_actions[action_id]
      _action_results[action_id] = result

      logger.info(f"Action {action_id} confirmed and executed")
      return result

    except Exception as e:
      result = ActionResult(
        action_id=action_id,
        action_type=action.action_type,
        status="failed",
        error=str(e),
      )

      del _pending_actions[action_id]
      _action_results[action_id] = result

      logger.error(f"Action {action_id} execution failed: {e}")
      return result

  except CarloError:
    raise
  except Exception as e:
    logger.error(f"Error confirming action: {e}")
    raise CarloError.from_exception(
      e,
      name="ACTION_CONFIRM_ERROR",
      source="actions",
      context="Failed to confirm action",
    )


@router.delete("/cancel/{action_id}")
async def cancel_action(action_id: str) -> Dict[str, str]:
  """
  Cancel a pending action
  """
  try:
    if action_id not in _pending_actions:
      raise CarloError(
        description=f"Action {action_id} not found",
        name="ACTION_NOT_FOUND",
        source="actions",
      )

    del _pending_actions[action_id]

    if action_id in _action_results:
      _action_results[action_id].status = "cancelled"

    logger.info(f"Action {action_id} cancelled")
    return {"message": f"Action {action_id} cancelled successfully"}

  except CarloError:
    raise
  except Exception as e:
    logger.error(f"Error cancelling action: {e}")
    raise CarloError.from_exception(
      e,
      name="ACTION_CANCEL_ERROR",
      source="actions",
      context="Failed to cancel action",
    )


@router.get("/result/{action_id}", response_model=ActionResult)
async def get_action_result(action_id: str) -> ActionResult:
  """
  Get the result of an action
  """
  try:
    if action_id not in _action_results:
      raise CarloError(
        description=f"Action {action_id} not found",
        name="ACTION_RESULT_NOT_FOUND",
        source="actions",
      )

    return _action_results[action_id]

  except CarloError:
    raise
  except Exception as e:
    logger.error(f"Error getting action result: {e}")
    raise CarloError.from_exception(
      e,
      name="ACTION_RESULT_ERROR",
      source="actions",
      context="Failed to retrieve action result",
    )


@router.get("/history", response_model=List[ActionResult])
async def get_action_history(limit: int = 50) -> List[ActionResult]:
  """
  Get history of executed actions
  """
  try:
    # Return recent action results
    results = list(_action_results.values())
    results.sort(key=lambda x: x.executed_at or datetime.min, reverse=True)
    return results[:limit]

  except Exception as e:
    logger.error(f"Error getting action history: {e}")
    raise CarloError.from_exception(
      e,
      name="ACTION_HISTORY_ERROR",
      source="actions",
      context="Failed to retrieve action history",
    )
