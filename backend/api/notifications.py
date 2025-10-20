"""
Notifications API endpoints
Handles notification scheduling and preparation
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import yaml
from pathlib import Path

from backend.exceptions import AppError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationType(BaseModel):
  """Configuration for a notification type"""

  name: str
  time: str | List[str]  # "HH:MM" or ["HH:MM", "HH:MM"] for range
  frequency: float = Field(default=1.0, ge=0.0, le=1.0)
  prompt: str
  enabled: bool = True


class NotificationConfig(BaseModel):
  """Complete notification configuration"""

  notifications: List[NotificationType]


class NotificationStatus(BaseModel):
  """Status of notification preparation"""

  last_preparation: Optional[datetime]
  next_preparation: datetime
  notifications_scheduled: int
  status: str


class ScheduledNotification(BaseModel):
  """A scheduled notification"""

  notification_id: str
  scheduled_time: datetime
  notification_type: str
  content: Optional[str] = None
  status: str = "pending"  # pending, delivered, failed


# In-memory storage for demo (should be persistent in production)
_notification_state = {"last_preparation": None, "scheduled_notifications": []}


def load_notification_config() -> NotificationConfig:
  """Load notification configuration from YAML file"""
  config_path = Path("config/notifications.yaml")

  if not config_path.exists():
    # Return default config if file doesn't exist
    return NotificationConfig(
      notifications=[
        NotificationType(
          name="morning_greeting",
          time="09:00",
          frequency=1.0,
          prompt="Generate a friendly morning greeting for the user",
        ),
        NotificationType(
          name="evening_reflection",
          time=["19:00", "21:00"],
          frequency=0.8,
          prompt="Ask the user about their day and suggest reflection",
        ),
      ]
    )

  try:
    with open(config_path, "r") as f:
      data = yaml.safe_load(f)
      return NotificationConfig(**data)
  except Exception as e:
    logger.error(f"Failed to load notification config: {e}")
    raise


def save_notification_state(state: Dict[str, Any]) -> None:
  """Save notification state to persistent storage"""
  # For now, just update in-memory state
  # In production, this would save to a database or file
  global _notification_state
  _notification_state.update(state)


def load_notification_state() -> Dict[str, Any]:
  """Load notification state from persistent storage"""
  # For now, return in-memory state
  # In production, this would load from a database or file
  return _notification_state


@router.get("/config", response_model=NotificationConfig)
async def get_notification_config() -> NotificationConfig:
  """
  Get current notification configuration
  """
  try:
    return load_notification_config()
  except Exception as e:
    logger.error(f"Error loading notification config: {e}")
    raise AppError.from_exception(
      e,
      name="NOTIFICATION_CONFIG_LOAD_ERROR",
      source="notifications",
      context="Failed to load notification configuration",
    )


@router.post("/config")
async def update_notification_config(config: NotificationConfig) -> Dict[str, str]:
  """
  Update notification configuration
  """
  try:
    # Save configuration to YAML file
    config_path = Path("config/notifications.yaml")
    config_path.parent.mkdir(exist_ok=True)

    with open(config_path, "w") as f:
      yaml.dump(config.dict(), f, default_flow_style=False)

    logger.info("Notification configuration updated")
    return {"message": "Configuration updated successfully"}

  except Exception as e:
    logger.error(f"Error updating notification config: {e}")
    raise AppError.from_exception(
      e,
      name="NOTIFICATION_CONFIG_UPDATE_ERROR",
      source="notifications",
      context="Failed to update notification configuration",
    )


@router.post("/prepare", response_model=NotificationStatus)
async def prepare_notifications() -> NotificationStatus:
  """
  Prepare notifications for the next day
  """
  try:
    state = load_notification_state()
    config = load_notification_config()

    now = datetime.now()
    tomorrow = now + timedelta(days=1)

    # Check if already prepared today
    last_prep = state.get("last_preparation")
    if last_prep:
      last_prep_date = (
        datetime.fromisoformat(last_prep) if isinstance(last_prep, str) else last_prep
      )
      if last_prep_date.date() == now.date():
        return NotificationStatus(
          last_preparation=last_prep_date,
          next_preparation=tomorrow.replace(hour=0, minute=0, second=0),
          notifications_scheduled=len(state.get("scheduled_notifications", [])),
          status="already_prepared_today",
        )

    # Schedule notifications for tomorrow
    scheduled = []
    for notif in config.notifications:
      if not notif.enabled:
        continue

      # Check frequency (probability)
      import random

      if random.random() > notif.frequency:
        continue

      # Determine time
      if isinstance(notif.time, str):
        # Fixed time
        hour, minute = map(int, notif.time.split(":"))
        scheduled_time = tomorrow.replace(hour=hour, minute=minute, second=0)
      else:
        # Random time within range
        start_hour, start_min = map(int, notif.time[0].split(":"))
        end_hour, end_min = map(int, notif.time[1].split(":"))

        # Convert to minutes for easier calculation
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min

        # Random time between start and end
        random_minutes = random.randint(start_minutes, end_minutes)
        hour = random_minutes // 60
        minute = random_minutes % 60

        scheduled_time = tomorrow.replace(hour=hour, minute=minute, second=0)

      # Create scheduled notification
      scheduled_notif = ScheduledNotification(
        notification_id=f"{notif.name}_{scheduled_time.timestamp()}",
        scheduled_time=scheduled_time,
        notification_type=notif.name,
        status="pending",
      )

      scheduled.append(scheduled_notif.dict())

    # Save state
    state["last_preparation"] = now.isoformat()
    state["scheduled_notifications"] = scheduled
    save_notification_state(state)

    logger.info(f"Prepared {len(scheduled)} notifications for tomorrow")

    return NotificationStatus(
      last_preparation=now,
      next_preparation=tomorrow.replace(hour=0, minute=0, second=0),
      notifications_scheduled=len(scheduled),
      status="success",
    )

  except Exception as e:
    logger.error(f"Error preparing notifications: {e}")
    raise AppError.from_exception(
      e,
      name="NOTIFICATION_PREPARE_ERROR",
      source="notifications",
      context="Failed to prepare notifications",
    )


@router.get("/scheduled", response_model=List[ScheduledNotification])
async def get_scheduled_notifications() -> List[ScheduledNotification]:
  """
  Get list of scheduled notifications
  """
  try:
    state = load_notification_state()
    scheduled = state.get("scheduled_notifications", [])

    # Convert to ScheduledNotification objects
    notifications = []
    for notif_dict in scheduled:
      # Handle datetime conversion
      if isinstance(notif_dict["scheduled_time"], str):
        notif_dict["scheduled_time"] = datetime.fromisoformat(
          notif_dict["scheduled_time"]
        )
      notifications.append(ScheduledNotification(**notif_dict))

    return notifications

  except Exception as e:
    logger.error(f"Error getting scheduled notifications: {e}")
    raise AppError.from_exception(
      e,
      name="SCHEDULED_NOTIFICATIONS_ERROR",
      source="notifications",
      context="Failed to retrieve scheduled notifications",
    )


@router.delete("/scheduled/{notification_id}")
async def cancel_notification(notification_id: str) -> Dict[str, str]:
  """
  Cancel a scheduled notification
  """
  try:
    state = load_notification_state()
    scheduled = state.get("scheduled_notifications", [])

    # Find and remove notification
    original_count = len(scheduled)
    scheduled = [n for n in scheduled if n.get("notification_id") != notification_id]

    if len(scheduled) == original_count:
      raise AppError(
        description=f"Notification {notification_id} not found",
        name="NOTIFICATION_NOT_FOUND",
        source="notifications",
      )

    state["scheduled_notifications"] = scheduled
    save_notification_state(state)

    return {"message": f"Notification {notification_id} cancelled"}

  except AppError:
    raise
  except Exception as e:
    logger.error(f"Error cancelling notification: {e}")
    raise AppError.from_exception(
      e,
      name="NOTIFICATION_CANCEL_ERROR",
      source="notifications",
      context="Failed to cancel notification",
    )


@router.post("/test")
async def test_notification() -> Dict[str, str]:
  """
  Send a test notification immediately
  """
  try:
    # This would integrate with the OS interface to send a real notification
    # For now, just return a success message
    logger.info("Test notification requested")

    return {
      "message": "Test notification sent",
      "content": "This is a test notification from Carlo",
      "timestamp": datetime.now().isoformat(),
    }

  except Exception as e:
    logger.error(f"Error sending test notification: {e}")
    raise AppError.from_exception(
      e,
      name="TEST_NOTIFICATION_ERROR",
      source="notifications",
      context="Failed to send test notification",
    )
