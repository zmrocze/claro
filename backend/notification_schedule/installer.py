"""
Systemd unit installer for Carlo notification scheduler.

This module manages installation and uninstallation of systemd user units that
schedule daily notification preparation via the `carlo-schedule-notifications` command.

Architecture:
  - Uses pystemd to communicate with systemd via D-Bus (user mode, no root required)
  - Links unit files from this package into ~/.config/systemd/user/ via symlinks
  - Enables and starts the timer unit to run daily

Key systemd concepts:
  - User units: Run in user session, stored in ~/.config/systemd/user/
  - LinkUnitFiles: Creates symlinks to unit files (preferred over copying)
  - Timer units: Trigger service units on schedule
  - D-Bus: IPC mechanism systemd uses for management operations
"""

import logging
from pathlib import Path
from importlib.resources import files

from pystemd.dbuslib import DBus
from pystemd.systemd1 import Manager

logger = logging.getLogger(__name__)

SERVICE_NAME = "claro-notification-scheduler.service"
TIMER_NAME = "claro-notification-scheduler.timer"


def _get_unit_template_paths() -> tuple[str, str]:
  """Locate unit template files from package resources.

  Returns:
    Tuple of (service_path, timer_path) as absolute paths
  """
  templates_dir = files("backend.notification_schedule").joinpath("templates/units")
  service_path = str(templates_dir.joinpath(SERVICE_NAME))
  timer_path = str(templates_dir.joinpath(TIMER_NAME))

  if not Path(service_path).exists():
    raise FileNotFoundError(f"Service template not found: {service_path}")
  if not Path(timer_path).exists():
    raise FileNotFoundError(f"Timer template not found: {timer_path}")

  logger.debug(f"Located unit templates: {service_path}, {timer_path}")
  return service_path, timer_path


def _check_units_linked(manager: Manager) -> tuple[bool, bool]:
  """Check if units are already linked in systemd.

  Args:
    manager: pystemd Manager instance

  Returns:
    Tuple of (service_linked, timer_linked)
  """
  # ListUnitFiles returns list of (unit_name, state) tuples
  unit_files = manager.Manager.ListUnitFiles()

  service_linked = any(SERVICE_NAME.encode() in uf[0] for uf in unit_files)
  timer_linked = any(TIMER_NAME.encode() in uf[0] for uf in unit_files)

  logger.debug(f"Units linked check: service={service_linked}, timer={timer_linked}")
  return service_linked, timer_linked


def ensure_notification_scheduler_units_installed() -> None:
  """Install and enable systemd units for daily notification scheduling.

  This function is idempotent - safe to call multiple times.

  Steps:
    1. Locate unit template files from package resources
    2. Connect to systemd via D-Bus (user mode)
    3. Link unit files if not already linked (creates symlinks)
    4. Reload systemd daemon to recognize units
    5. Enable timer unit (persistent across reboots)
    6. Start timer unit immediately

  Raises:
    FileNotFoundError: If unit template files are missing
    Exception: If systemd operations fail
  """
  logger.info("Installing Carlo notification scheduler units...")

  try:
    service_path, timer_path = _get_unit_template_paths()

    # Connect to systemd via D-Bus in user mode (no root required)
    # Why user mode: These units run in the user session, not system-wide
    with DBus(user_mode=True) as bus:
      manager = Manager(bus=bus)
      manager.load()

      service_linked, timer_linked = _check_units_linked(manager)

      # Link units if not already present
      # Why LinkUnitFiles: Creates symlinks from ~/.config/systemd/user/ to our
      # package templates, avoiding duplication and ensuring updates propagate
      if not (service_linked and timer_linked):
        logger.info("Linking unit files to systemd...")
        paths_to_link = []
        if not service_linked:
          paths_to_link.append(service_path.encode())
        if not timer_linked:
          paths_to_link.append(timer_path.encode())

        manager.Manager.LinkUnitFiles(
          paths_to_link, False, True
        )  # runtime=False, force=True
        logger.info(
          f"Linked units: {', '.join(Path(p.decode()).name for p in paths_to_link)}"
        )
      else:
        logger.info("Units already linked, skipping link step")

      # Reload systemd to recognize new/changed units
      logger.info("Reloading systemd daemon...")
      manager.Manager.Reload()

      # Enable timer (idempotent operation)
      # This makes the timer start automatically on user login
      logger.info(f"Enabling {TIMER_NAME}...")
      manager.Manager.EnableUnitFiles(
        [TIMER_NAME.encode()], False, True
      )  # runtime=False, force=True

      # Start timer immediately (idempotent - safe if already running)
      logger.info(f"Starting {TIMER_NAME}...")
      manager.Manager.StartUnit(TIMER_NAME.encode(), b"replace")

      logger.info("✓ Installation complete! Timer is now active.")
      logger.info(f"  Check status: systemctl --user status {TIMER_NAME}")
      logger.info(f"  View logs: journalctl --user -u {SERVICE_NAME}")

  except Exception as e:
    logger.error(f"Failed to install notification scheduler units: {e}")
    raise


def uninstall_scheduler_units() -> None:
  """Uninstall and disable notification scheduler units.

  For testing and development. Stops timer, disables auto-start, and reloads systemd.
  The symlinks in ~/.config/systemd/user/ will remain but units will be disabled.

  Steps:
    1. Stop timer unit if running
    2. Disable timer unit (removes auto-start)
    3. Reload systemd daemon

  Raises:
    Exception: If systemd operations fail
  """
  logger.info("Uninstalling Carlo notification scheduler units...")

  try:
    with DBus(user_mode=True) as bus:
      manager = Manager(bus=bus)
      manager.load()

      # Stop timer if running (idempotent - safe if not running)
      try:
        logger.info(f"Stopping {TIMER_NAME}...")
        manager.Manager.StopUnit(TIMER_NAME.encode(), b"replace")
        logger.info("Timer stopped")
      except Exception as e:
        logger.warning(f"Could not stop timer (may not be running): {e}")

      # Disable timer (removes auto-start on login)
      logger.info(f"Disabling {TIMER_NAME}...")
      manager.Manager.DisableUnitFiles([TIMER_NAME.encode()], False)  # runtime=False
      logger.info("Timer disabled")

      # Reload systemd to apply changes
      logger.info("Reloading systemd daemon...")
      manager.Manager.Reload()

      logger.info("✓ Uninstallation complete!")
      logger.info("  Note: Unit files remain linked but are disabled.")
      logger.info(
        f"  To manually remove links: rm ~/.config/systemd/user/{SERVICE_NAME} ~/.config/systemd/user/{TIMER_NAME}"
      )

  except Exception as e:
    logger.error(f"Failed to uninstall notification scheduler units: {e}")
    raise
