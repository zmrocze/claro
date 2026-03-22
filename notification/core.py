"""Core notification logic, shared by CLI and Android service."""

import logging
from pathlib import Path

from backend.agent.agent import new_agent
from backend.sessions import get_session_manager
from notification_schedule import parse_notification_config
from os_interfaces.base import OSImplementations, set_os_implementations

logger = logging.getLogger(__name__)


async def get_claro_response(prompt: str) -> str:
  """Get response from Carlo agent for the given prompt."""
  try:
    agent = new_agent()
    return await agent.ainvoke(prompt)
  except Exception as e:
    logger.error(f"Failed to get Carlo response: {e}")
    return f"Error: {str(e)}"


async def fire_notification(
  notification_name: str,
  config_path: Path,
  os_impl: OSImplementations,
  on_clicked=None,
  on_dismissed=None,
) -> str:
  """Look up notification by name, call LLM, create session, show notification.

  Args:
      notification_name: Name from notification_schedule.yaml
      config_path: Path to notification_schedule.yaml
      os_impl: Platform OS implementations
      on_clicked: Optional callback when notification is clicked
      on_dismissed: Optional callback when notification is dismissed

  Returns:
      session_id of the created conversation session
  """
  set_os_implementations(os_impl)

  config = parse_notification_config(config_path)
  if notification_name not in config.notifications:
    available = ", ".join(config.notifications.keys())
    raise KeyError(
      f"Notification '{notification_name}' not found. Available: {available}"
    )

  prompt = config.notifications[notification_name].calling
  logger.info(
    f"Using notification '{notification_name}' with prompt: {prompt[:100]}..."
  )

  response = await get_claro_response(prompt)
  logger.info(f"Got response: {response[:100]}...")

  session_manager = get_session_manager()
  session_id = session_manager.create_session()
  logger.info(f"Created session {session_id} for notification")
  session_manager.add_message(session_id=session_id, content=response, role="assistant")

  display_text = response[:200] + ("..." if len(response) > 200 else "")
  notifier = os_impl.notification_manager(app_name="Carlo")
  await notifier.create_notification(
    title="Carlo", body=display_text, on_clicked=on_clicked, on_dismissed=on_dismissed
  )
  logger.info("Notification created successfully")
  return session_id
