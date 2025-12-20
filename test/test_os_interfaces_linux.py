"""Tests for Linux OS interfaces"""

from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from os_interfaces.base import ScheduleTimeRange, TimerConfig
from os_interfaces.linux import (
  LinuxNotificationManager,
  LinuxTimerManager,
)


class TestLinuxNotificationManager:
  """Tests for LinuxNotificationManager"""

  @patch("os_interfaces.linux.DesktopNotifier")
  def test_init(self, mock_notifier_class):
    """Test notification manager initialization"""
    manager = LinuxNotificationManager(app_name="TestApp")
    mock_notifier_class.assert_called_once_with(app_name="TestApp")
    assert manager.notifier is not None

  @pytest.mark.asyncio
  @patch("os_interfaces.linux.DesktopNotifier")
  async def test_create_notification_no_loop(self, mock_notifier_class):
    """Test creating notification"""
    mock_notifier = MagicMock()
    mock_notifier.send = AsyncMock()
    mock_notifier_class.return_value = mock_notifier

    manager = LinuxNotificationManager(app_name="TestApp")
    await manager.create_notification("Test Title", "Test Body")

    mock_notifier.send.assert_called_once_with(
      title="Test Title", message="Test Body", on_clicked=None, on_dismissed=None
    )

  @pytest.mark.asyncio
  @patch("os_interfaces.linux.DesktopNotifier")
  async def test_create_notification_with_loop(self, mock_notifier_class):
    """Test creating notification with running event loop"""
    mock_notifier = MagicMock()
    mock_notifier.send = AsyncMock()
    mock_notifier_class.return_value = mock_notifier

    manager = LinuxNotificationManager(app_name="TestApp")
    await manager.create_notification("Test Title", "Test Body")

    mock_notifier.send.assert_called_once_with(
      title="Test Title", message="Test Body", on_clicked=None, on_dismissed=None
    )

  @pytest.mark.asyncio
  @patch("os_interfaces.linux.DesktopNotifier")
  async def test_create_notification_with_callback(self, mock_notifier_class):
    """Test creating notification with on_clicked callback"""
    mock_notifier = MagicMock()
    mock_notifier.send = AsyncMock()
    mock_notifier_class.return_value = mock_notifier

    manager = LinuxNotificationManager(app_name="TestApp")
    callback = MagicMock()
    await manager.create_notification("Test Title", "Test Body", on_clicked=callback)

    # Verify send was called with on_clicked parameter
    mock_notifier.send.assert_called_once_with(
      title="Test Title", message="Test Body", on_clicked=callback, on_dismissed=None
    )


class TestLinuxTimerManager:
  """Tests for LinuxTimerManager"""

  def test_init(self):
    manager = LinuxTimerManager(app_name="TestApp")
    assert manager.app_name == "TestApp"

  @patch("os_interfaces.linux.DBus")
  @patch("os_interfaces.linux.Manager")
  @patch("os_interfaces.linux.Path.write_text")
  def test_schedule_timer_with_time(
    self, mock_write, mock_manager_class, mock_dbus_class
  ):
    """Test schedule_timer with specific time"""
    mock_dbus = MagicMock()
    mock_dbus_class.return_value.__enter__ = MagicMock(return_value=mock_dbus)
    mock_dbus_class.return_value.__exit__ = MagicMock(return_value=None)
    mock_manager = MagicMock()
    mock_manager.Manager.ListUnitFiles.return_value = []
    mock_manager.Manager.EnableUnitFiles = MagicMock()
    mock_manager.Manager.StartUnit = MagicMock()
    mock_manager.Manager.Reload = MagicMock()
    mock_manager_class.return_value = mock_manager

    manager = LinuxTimerManager(app_name="TestApp")
    cfg = TimerConfig(
      timing=datetime(2025, 1, 2, 14, 30),
      command="/usr/bin/echo",
      args=["test"],
      name="morning",
    )
    timer_id = manager.schedule_timer(cfg)

    assert timer_id is not None
    assert mock_write.call_count == 2  # service + timer files
    # Check service unit includes cleanup
    service_content = mock_write.call_args_list[0][0][0]
    assert "ExecStopPost" in service_content
    assert "systemctl --user clean --what=all" in service_content
    assert "daemon-reload" in service_content
    # Check OnCalendar format in timer unit
    timer_content = mock_write.call_args_list[1][0][0]
    assert "OnCalendar=2025-01-02 14:30:00" in timer_content
    assert "RandomizedDelaySec" not in timer_content

  @patch("os_interfaces.linux.DBus")
  @patch("os_interfaces.linux.Manager")
  @patch("os_interfaces.linux.Path.write_text")
  def test_schedule_timer_with_timerange(
    self, mock_write, mock_manager_class, mock_dbus_class
  ):
    """Test schedule_timer with TimeRange uses RandomizedDelaySec"""
    mock_dbus = MagicMock()
    mock_dbus_class.return_value.__enter__ = MagicMock(return_value=mock_dbus)
    mock_dbus_class.return_value.__exit__ = MagicMock(return_value=None)
    mock_manager = MagicMock()
    mock_manager.Manager.ListUnitFiles.return_value = []
    mock_manager.Manager.EnableUnitFiles = MagicMock()
    mock_manager.Manager.StartUnit = MagicMock()
    mock_manager.Manager.Reload = MagicMock()
    mock_manager_class.return_value = mock_manager

    manager = LinuxTimerManager(app_name="TestApp")
    tr = ScheduleTimeRange(
      from_time=datetime(2025, 1, 2, 9, 0), to_time=datetime(2025, 1, 2, 11, 0)
    )
    cfg = TimerConfig(timing=tr, command="/usr/bin/echo", name="flex")
    timer_id = manager.schedule_timer(cfg)

    assert timer_id is not None
    timer_content = mock_write.call_args_list[1][0][0]
    assert "OnCalendar=2025-01-02 09:00:00" in timer_content
    assert "RandomizedDelaySec=7200s" in timer_content  # 2 hours

  @patch("os_interfaces.linux.DBus")
  @patch("os_interfaces.linux.Manager")
  @patch("os_interfaces.linux.Path.write_text")
  def test_schedule_timer_naming(self, mock_write, mock_manager_class, mock_dbus_class):
    """Test schedule_timer generates names with optional name field"""
    mock_dbus = MagicMock()
    mock_dbus_class.return_value.__enter__ = MagicMock(return_value=mock_dbus)
    mock_dbus_class.return_value.__exit__ = MagicMock(return_value=None)
    mock_manager = MagicMock()
    mock_manager.Manager.ListUnitFiles.return_value = []
    mock_manager.Manager.EnableUnitFiles = MagicMock()
    mock_manager.Manager.StartUnit = MagicMock()
    mock_manager.Manager.Reload = MagicMock()
    mock_manager_class.return_value = mock_manager

    manager = LinuxTimerManager(app_name="claro")
    cfg1 = TimerConfig(
      timing=datetime(2025, 1, 2, 9, 0), command="/bin/true", name="test"
    )
    cfg2 = TimerConfig(
      timing=datetime(2025, 1, 2, 9, 0), command="/bin/true"
    )  # no name

    id1 = manager.schedule_timer(cfg1)
    id2 = manager.schedule_timer(cfg2)

    assert "test" in id1
    assert "test" not in id2

  @patch("os_interfaces.linux.DBus")
  @patch("os_interfaces.linux.Manager")
  @patch("os_interfaces.linux.Path.write_text")
  def test_schedule_daily_creates_units(
    self, mock_write, mock_manager_class, mock_dbus_class
  ):
    """Test schedule_daily creates unit files when they don't exist"""
    mock_dbus = MagicMock()
    mock_dbus_class.return_value.__enter__ = MagicMock(return_value=mock_dbus)
    mock_dbus_class.return_value.__exit__ = MagicMock(return_value=None)
    mock_manager = MagicMock()
    mock_manager.Manager.ListUnitFiles.return_value = []  # no units exist
    mock_manager.Manager.EnableUnitFiles = MagicMock()
    mock_manager.Manager.StartUnit = MagicMock()
    mock_manager.Manager.Reload = MagicMock()
    mock_manager_class.return_value = mock_manager

    manager = LinuxTimerManager(app_name="claro")
    manager.schedule_daily("/usr/bin/notify", ["--daily"], time(9, 0))

    assert mock_write.call_count == 2  # service + timer
    service_content = mock_write.call_args_list[0][0][0]
    timer_content = mock_write.call_args_list[1][0][0]
    assert "ExecStart=/usr/bin/notify --daily" in service_content
    assert "OnCalendar=*-*-* 09:00:00" in timer_content
    assert "Persistent=true" in timer_content
    mock_manager.Manager.Reload.assert_called_once()

  @patch("os_interfaces.linux.DBus")
  @patch("os_interfaces.linux.Manager")
  @patch("os_interfaces.linux.Path.write_text")
  def test_schedule_daily_idempotent(
    self, mock_write, mock_manager_class, mock_dbus_class
  ):
    """Test schedule_daily is idempotent when units already exist"""
    mock_dbus = MagicMock()
    mock_dbus_class.return_value.__enter__ = MagicMock(return_value=mock_dbus)
    mock_dbus_class.return_value.__exit__ = MagicMock(return_value=None)
    mock_manager = MagicMock()
    # units already exist
    mock_manager.Manager.ListUnitFiles.return_value = [
      (b"/path/claro-claro-notification-scheduler.service", b"enabled"),
      (b"/path/claro-claro-notification-scheduler.timer", b"enabled"),
    ]
    mock_manager.Manager.EnableUnitFiles = MagicMock()
    mock_manager.Manager.StartUnit = MagicMock()
    mock_manager.Manager.Reload = MagicMock()
    mock_manager_class.return_value = mock_manager

    manager = LinuxTimerManager(app_name="claro")
    manager.schedule_daily("/usr/bin/notify", [], time(9, 0))

    # Should not write files or reload
    mock_write.assert_not_called()
    mock_manager.Manager.Reload.assert_not_called()
    # But should still enable/start
    mock_manager.Manager.EnableUnitFiles.assert_called_once()
    mock_manager.Manager.StartUnit.assert_called_once()

  @patch("os_interfaces.linux.DBus")
  @patch("os_interfaces.linux.Manager")
  def test_cancel_timer(self, mock_manager_class, mock_dbus_class):
    """Test cancel_timer stops and disables the timer"""
    mock_dbus = MagicMock()
    mock_dbus_class.return_value.__enter__ = MagicMock(return_value=mock_dbus)
    mock_dbus_class.return_value.__exit__ = MagicMock(return_value=None)
    mock_manager = MagicMock()
    mock_manager.Manager.StopUnit = MagicMock()
    mock_manager.Manager.DisableUnitFiles = MagicMock()
    mock_manager_class.return_value = mock_manager

    manager = LinuxTimerManager(app_name="TestApp")
    manager.cancel_timer("test-unit")

    mock_manager.Manager.StopUnit.assert_called_once_with(
      b"test-unit.timer", b"replace"
    )
    mock_manager.Manager.DisableUnitFiles.assert_called_once_with(
      [b"test-unit.timer"], False
    )
