"""
Send system notifications using named prompts from a YAML config.

Reads notification configuration from ~/.config/claro/notification_schedule.yaml
(on Linux) and triggers the specified notification using the Carlo agent.

Usage:
    uv run python -m notification.main <notification_name>
"""

import argparse
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

from platformdirs import user_config_dir
from backend.agent.agent import new_agent
from notification_schedule import parse_notification_config
from os_interfaces.base import OSImplementations
from os_interfaces.linux import LinuxNotificationManager

logging.basicConfig(
  level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def open_app_on_click() -> None:
  """Callback to open an app when notification is clicked.

  Opens Firefox as a test app (commonly installed on GNOME Linux).
  This will be replaced with the Claro app deep link later.
  """
  try:
    # Use xdg-open to open Firefox (or default browser)
    # This is a common app on GNOME Linux systems
    subprocess.Popen(
      ["xdg-open", "https://www.mozilla.org"],
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
    )
    logger.info("Opened app via deep link")
  except Exception as e:
    logger.error(f"Failed to open app: {e}")


async def get_claro_response(prompt: str) -> str:
  """Get response from Carlo agent for the given prompt.

  Args:
      prompt: User prompt to send to Carlo

  Returns:
      Agent's response text
  """
  try:
    agent = new_agent()
    response = await agent.ainvoke(prompt)
    return response
  except Exception as e:
    logger.error(f"Failed to get Carlo response: {e}")
    return f"Error: {str(e)}"


async def create_notification(
  response_text: str,
  done_event: asyncio.Event,
  os_impl: OSImplementations,
) -> None:
  """Create a system notification with the response text.

  Args:
      response_text: Text to display in the notification
      done_event: Event to signal when notification is clicked or dismissed
  """
  notifier = os_impl.notification_manager(app_name="Carlo")

  # Truncate response if too long for notification
  max_length = 200
  display_text = response_text[:max_length]
  if len(response_text) > max_length:
    display_text += "..."

  def on_clicked():
    """Handle notification click."""
    open_app_on_click()
    done_event.set()

  def on_dismissed():
    """Handle notification dismissal."""
    logger.info("Notification dismissed")
    done_event.set()

  await notifier.create_notification(
    title="Carlo", body=display_text, on_clicked=on_clicked, on_dismissed=on_dismissed
  )
  logger.info("Notification created successfully")


async def main(os_impl: OSImplementations | None = None) -> None:
  """Main entrypoint function.

  Args:
      prompt: User prompt (if None, reads from config using command line args)
  """
  # Parse command line arguments
  parser = argparse.ArgumentParser(
    description="Send a system notification using a named prompt from the notification schedule config."
  )
  parser.add_argument(
    "notification-name",
    help="Name of the notification to trigger (must exist in notification_schedule.yaml)",
  )
  args = parser.parse_args()

  if os_impl is None:
    os_impl = OSImplementations(
      notification_manager_cls=LinuxNotificationManager,
      timer_manager_cls=lambda *a, **k: None,  # type: ignore[arg-type]
    )

  # Locate config file
  config_path = (
    Path(user_config_dir("claro", ensure_exists=True)) / "notification_schedule.yaml"
  )

  # Load config
  try:
    config = parse_notification_config(config_path)
  except Exception as e:
    logger.error(f"Error opening config file: {e}")
    sys.exit(1)

  # Look up notification by name
  if args.notification_name not in config.notifications:
    available = ", ".join(config.notifications.keys())
    logger.error(f"Notification '{args.notification_name}' not found in config.")
    logger.error(f"Available notifications: {available}")
    sys.exit(1)

  prompt = config.notifications[args.notification_name].calling
  logger.info(
    f"Using notification '{args.notification_name}' with prompt: {prompt[:100]}..."
  )

  # Get response from Carlo agent
  response = await get_claro_response(prompt)
  logger.info(f"Got response: {response[:100]}...")

  # Create event to signal when notification is interacted with
  done_event = asyncio.Event()

  # Create notification with response
  await create_notification(response, done_event, os_impl)

  # Wait for user to click or dismiss the notification
  logger.info("Waiting for notification interaction...")
  await done_event.wait()
  logger.info("Notification interaction complete, exiting")


if __name__ == "__main__":
  asyncio.run(main())
