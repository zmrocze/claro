"""
Entrypoint for creating notifications with Carlo agent responses.

Usage:
    python notify_with_carlo.py "Your prompt here"
"""

import asyncio
import logging
import subprocess
import sys
from typing import Optional

from backend.agent.agent import new_agent
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


async def get_carlo_response(prompt: str) -> str:
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


async def create_notification(response_text: str, done_event: asyncio.Event) -> None:
  """Create a system notification with the response text.

  Args:
      response_text: Text to display in the notification
      done_event: Event to signal when notification is clicked or dismissed
  """
  notifier = LinuxNotificationManager(app_name="Carlo")

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


async def main(prompt: Optional[str] = None) -> None:
  """Main entrypoint function.

  Args:
      prompt: User prompt (if None, reads from command line args)
  """
  if prompt is None:
    if len(sys.argv) < 2:
      print("Usage: python notify_with_carlo.py 'Your prompt here'")
      sys.exit(1)
    prompt = " ".join(sys.argv[1:])

  logger.info(f"Processing prompt: {prompt}")

  # Get response from Carlo agent
  response = await get_carlo_response(prompt)
  logger.info(f"Got response: {response[:100]}...")

  # Create event to signal when notification is interacted with
  done_event = asyncio.Event()

  # Create notification with response
  await create_notification(response, done_event)

  # Wait for user to click or dismiss the notification
  logger.info("Waiting for notification interaction...")
  await done_event.wait()
  logger.info("Notification interaction complete, exiting")


if __name__ == "__main__":
  asyncio.run(main())
