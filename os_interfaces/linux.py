"""Linux-specific implementations of OS interfaces"""

import logging
from contextlib import contextmanager
from datetime import time
from pathlib import Path
import shutil
from typing import Callable, Optional

from desktop_notifier import DesktopNotifier
from pystemd.dbuslib import DBus
from pystemd.systemd1 import Manager

from .base import (
  NotificationManager,
  ScheduleTimeRange,
  TimerConfig,
  TimerManager,
)

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
  """Linux timer manager using persistent systemd user units"""

  def __init__(self, app_name: str):
    self.app_name = app_name

  # ---- helpers ----
  @contextmanager
  def _connect_systemd(self):
    with DBus(user_mode=True) as bus:
      manager = Manager(bus=bus)
      manager.load()
      yield manager

  def _user_unit_dir(self) -> Path:
    return Path.home() / ".config/systemd/user"

  def _write_unit(self, name: str, content: str) -> Path:
    d = self._user_unit_dir()
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(content)
    return p

  def _list_unit_files(self, manager: Manager) -> list[bytes]:
    return [u[0] for u in manager.Manager.ListUnitFiles()]

  def _unit_files_exist(self, manager: Manager, base: str) -> bool:
    files = self._list_unit_files(manager)
    return any(f.endswith(f"{base}.service".encode()) for f in files) and any(
      f.endswith(f"{base}.timer".encode()) for f in files
    )

  def _enable_and_start_timer(self, manager: Manager, timer: str) -> None:
    manager.Manager.EnableUnitFiles([f"{timer}.timer".encode()], False, True)
    manager.Manager.StartUnit(f"{timer}.timer".encode(), b"replace")

  def _reload(self, manager: Manager) -> None:
    manager.Manager.Reload()

  def _unit_name(self, prefix: str, name: str | None, time_info: str) -> str:
    """Generate unit name from prefix, notification name, and time."""
    base = f"{self.app_name}-{prefix}"
    if name:
      base += f"-{name}"
    base += f"-{time_info}"
    return base

  def _service_content(
    self,
    base: str,
    command: str,
    args: list[str],
    after: str | None = None,
    cleanup: bool = False,
  ) -> str:
    after_line = f"After={after}.timer\n" if after else ""
    exec_line = " ".join([command, *args])

    # Add cleanup for one-shot notification timers
    cleanup_line = ""
    if cleanup:
      unit_dir = self._user_unit_dir()
      cleanup_line = (
        f"ExecStopPost=/bin/sh -c '"
        f"systemctl --user stop {base}.timer; "
        f"systemctl --user clean --what=all {base}.service {base}.timer; "
        f"rm -f {unit_dir}/{base}.service {unit_dir}/{base}.timer; "
        f"systemctl --user daemon-reload'\n"
      )

    return (
      "[Unit]\n"
      f"Description={self.app_name} service {base}\n"
      f"{after_line}"
      "\n[Service]\n"
      "Type=oneshot\n"
      f"ExecStart={exec_line}\n"
      f"{cleanup_line}"
      "\n[Install]\n"
      f"WantedBy={self.app_name}.target\n"
    )

  def _timer_content(
    self, base: str, on_calendar: str, unit: str, randomized_delay: str | None = None
  ) -> str:
    rand = f"RandomizedDelaySec={randomized_delay}\n" if randomized_delay else ""
    return (
      "[Unit]\n"
      f"Description={self.app_name} timer {base}\n"
      f"After={unit}.service\n"
      "\n[Timer]\n"
      f"OnCalendar={on_calendar}\n"
      "Persistent=true\n"
      f"{rand}"
      f"Unit={unit}.service\n"
      "\n[Install]\n"
      "WantedBy=timers.target\n"
    )

  # ---- public API ----
  def schedule_timer(self, timer_config: TimerConfig) -> str:
    """Create persistent oneshot timer via unit files and start it"""
    t = timer_config.timing
    name_gist = (
      f"{t.from_time.strftime('%H%M')}-{t.to_time.strftime('%H%M')}"
      if isinstance(t, ScheduleTimeRange)
      else t.strftime("%H%M")
    )
    base = self._unit_name("notification", timer_config.name, name_gist)

    # systemd time expression and optional randomization
    if isinstance(t, ScheduleTimeRange):
      # ScheduleTimeRange with specific dates
      on_cal = f"{t.from_time.strftime('%Y-%m-%d %H:%M')}:00"
      delta = (t.to_time - t.from_time).seconds
      randomized = f"{delta}s"
    else:
      # Single datetime
      on_cal = f"{t.strftime('%Y-%m-%d %H:%M')}:00"
      randomized = None

    service_txt = self._service_content(
      base, timer_config.command, timer_config.args, cleanup=True
    )
    timer_txt = self._timer_content(base, on_cal, base, randomized)

    with self._connect_systemd() as m:
      self._write_unit(f"{base}.service", service_txt)
      self._write_unit(f"{base}.timer", timer_txt)
      self._reload(m)
      self._enable_and_start_timer(m, base)

    logger.info(f"Scheduled oneshot '{timer_config.command}' as {base} at {on_cal}")
    return base

  def schedule_daily(self, command: str, args: list[str], run_time: time) -> None:
    """Install/enable a daily scheduler; idempotent."""
    base = f"{self.app_name}-notification-scheduler"
    on_cal = f"*-*-* {run_time.strftime('%H:%M')}:00"

    exe_path = shutil.which(command) or command
    service_txt = self._service_content(base, exe_path, args)
    timer_txt = self._timer_content(base, on_cal, base)

    with self._connect_systemd() as m:
      if not self._unit_files_exist(m, base):
        self._write_unit(f"{base}.service", service_txt)
        self._write_unit(f"{base}.timer", timer_txt)
        self._reload(m)
        logger.info(f"Created daily scheduler units and reloaded: {base}")
      else:
        logger.info("Daily scheduler units already present")
        # Check if systemd knows about the timer; reload if not
        try:
          m.Manager.GetUnit(f"{base}.timer".encode())
        except Exception:
          logger.info("Units exist on disk but not loaded in systemd, reloading")
          self._reload(m)

      self._enable_and_start_timer(m, base)

  def cancel_timer(self, timer_id: str) -> None:
    """Stop and disable a timer. timer_id is the base unit name."""
    try:
      with self._connect_systemd() as m:
        try:
          m.Manager.StopUnit(f"{timer_id}.timer".encode(), b"replace")
          m.Manager.DisableUnitFiles([f"{timer_id}.timer".encode()], False)
          logger.info(f"Cancelled timer {timer_id}")
        except Exception as e:
          logger.warning(f"Could not cancel timer {timer_id}: {e}")
    except Exception as e:
      logger.error(f"Failed to cancel timer: {e}")
