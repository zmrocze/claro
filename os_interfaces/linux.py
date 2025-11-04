"""Linux-specific implementations of OS interfaces"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

import yaml
from desktop_notifier import DesktopNotifier
from platformdirs import user_config_dir
from pystemd.dbuslib import DBus
from pystemd.systemd1 import Manager

from .base import ConfigStorage, NotificationManager, TimerManager

logger = logging.getLogger(__name__)


class LinuxNotificationManager(NotificationManager):
  """Linux notification manager using desktop-notifier"""

  def __init__(self, app_name: str):
    self.notifier = DesktopNotifier(app_name=app_name)

  async def create_notification(
    self,
    title: str,
    body: str,
    on_clicked: Optional[Callable] = None,
    on_dismissed: Optional[Callable] = None,
  ) -> None:
    """Create and show a notification using desktop-notifier

    Args:
      title: Notification title
      body: Notification body text
      on_clicked: Optional callback when notification is clicked
      on_dismissed: Optional callback when notification is dismissed
    """
    try:
      # Send notification directly (we're already in an async context)
      await self.notifier.send(
        title=title, message=body, on_clicked=on_clicked, on_dismissed=on_dismissed
      )
      logger.info(f"Notification sent: {title}")
    except Exception as e:
      logger.error(f"Failed to send notification: {e}")


class LinuxTimerManager(TimerManager):
  """Linux timer manager using pystemd transient units"""

  def __init__(self, app_name: str):
    self.app_name = app_name
    self.timers: dict[str, str] = {}  # timer_id -> systemd unit name

  def schedule_timer(
    self, time: datetime, command: str, args: Optional[list[str]] = None
  ) -> str:
    """Schedule a timer to run a command using systemd transient units

    Creates both a service unit (to run the command) and a timer unit
    (to trigger the service at the specified time).
    """
    timer_id = str(uuid.uuid4())
    service_name = f"{self.app_name}-{timer_id}"
    timer_name = f"{service_name}.timer"

    try:
      # Calculate time until trigger
      now = datetime.now()
      if time <= now:
        logger.warning("Timer scheduled for past time, cannot schedule")
        return timer_id

      delay_seconds = int((time - now).total_seconds())

      with DBus(user_mode=True) as bus:
        manager = Manager(bus=bus)
        manager.load()

        # Build command with arguments
        cmd_args = [command]
        if args:
          cmd_args.extend(args)

        # Create service unit properties
        service_properties = {
          b"Type": b"oneshot",
          b"RemainAfterExit": False,
          b"ExecStart": [(command.encode(), [arg.encode() for arg in cmd_args], False)],
        }

        # Create timer unit properties
        timer_properties = {
          b"OnActiveSec": delay_seconds * 1000000,  # microseconds
          b"RemainAfterElapse": False,
          b"Unit": f"{service_name}.service".encode(),
        }

        # Start the service unit first (inactive, will be triggered by timer)
        manager.Manager.StartTransientUnit(
          f"{service_name}.service".encode(),
          b"fail",
          service_properties,
          [],
        )

        # Start the timer unit
        manager.Manager.StartTransientUnit(
          timer_name.encode(), b"fail", timer_properties, []
        )

      self.timers[timer_id] = service_name
      logger.info(f"Timer {timer_id} scheduled to run '{command}' at {time}")
      return timer_id

    except Exception as e:
      logger.error(f"Failed to schedule timer: {e}")
      return timer_id

  def cancel_timer(self, timer_id: str) -> None:
    """Cancel a scheduled timer"""
    if timer_id not in self.timers:
      logger.warning(f"Timer {timer_id} not found")
      return

    unit_name = self.timers[timer_id]

    try:
      with DBus(user_mode=True) as bus:
        manager = Manager(bus=bus)
        manager.load()

        # Stop the timer unit
        try:
          manager.Manager.StopUnit(f"{unit_name}.timer".encode(), b"fail")
          logger.info(f"Timer {timer_id} cancelled")
        except Exception as e:
          logger.debug(f"Timer unit may not exist: {e}")

      # Clean up
      del self.timers[timer_id]

    except Exception as e:
      logger.error(f"Failed to cancel timer: {e}")


class LinuxConfigStorage(ConfigStorage):
  """Linux configuration storage using YAML files in user config directory"""

  def __init__(self, app_name: str, config_name: str):
    self.config_dir = Path(user_config_dir(app_name, ensure_exists=True))
    self.config_file = self.config_dir / f"{config_name}.yaml"
    self._config: dict = {}
    self._load_config()

  def _load_config(self) -> None:
    """Load configuration from disk"""
    if self.config_file.exists():
      try:
        with open(self.config_file, "r") as f:
          self._config = yaml.safe_load(f) or {}
        logger.debug(f"Loaded config from {self.config_file}")
      except Exception as e:
        logger.error(f"Failed to load config: {e}")
        self._config = {}
    else:
      self._config = {}

  def load(self) -> dict:
    """Load configuration from storage"""
    self._load_config()
    return self._config.copy()

  def save(self, config: dict) -> None:
    """Save configuration to storage"""
    self._config = config.copy()
    try:
      self.config_dir.mkdir(parents=True, exist_ok=True)
      with open(self.config_file, "w") as f:
        yaml.safe_dump(self._config, f, default_flow_style=False)
      logger.debug(f"Saved config to {self.config_file}")
    except Exception as e:
      logger.error(f"Failed to save config: {e}")

  def get(self, key: str, default: Any = None) -> Any:
    """Get a configuration value by key"""
    return self._config.get(key, default)

  def set(self, key: str, value: Any) -> None:
    """Set a configuration value"""
    self._config[key] = value
    self.save(self._config)
