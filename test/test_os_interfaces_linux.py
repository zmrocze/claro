"""Tests for Linux OS interfaces"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from os_interfaces.linux import (
  LinuxConfigStorage,
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
    """Test timer manager initialization"""
    manager = LinuxTimerManager(app_name="TestApp")
    assert manager.app_name == "TestApp"
    assert manager.timers == {}

  @patch("os_interfaces.linux.DBus")
  @patch("os_interfaces.linux.Manager")
  def test_schedule_timer_future(self, mock_manager_class, mock_dbus_class):
    """Test scheduling a timer for future time"""
    mock_dbus = MagicMock()
    mock_dbus_class.return_value.__enter__ = MagicMock(return_value=mock_dbus)
    mock_dbus_class.return_value.__exit__ = MagicMock(return_value=None)

    mock_manager = MagicMock()
    mock_manager.Manager.StartTransientUnit = MagicMock()
    mock_manager_class.return_value = mock_manager

    manager = LinuxTimerManager(app_name="TestApp")
    future_time = datetime.now() + timedelta(seconds=10)

    timer_id = manager.schedule_timer(future_time, "/usr/bin/echo", ["Hello", "World"])

    assert timer_id in manager.timers
    # Verify both service and timer units were created
    assert mock_manager.Manager.StartTransientUnit.call_count == 2

  def test_schedule_timer_past(self):
    """Test scheduling a timer for past time returns without scheduling"""
    manager = LinuxTimerManager(app_name="TestApp")
    past_time = datetime.now() - timedelta(seconds=10)

    timer_id = manager.schedule_timer(past_time, "/usr/bin/echo", ["test"])

    # Timer ID is returned but nothing is scheduled
    assert timer_id is not None
    assert timer_id not in manager.timers

  @patch("os_interfaces.linux.DBus")
  @patch("os_interfaces.linux.Manager")
  def test_cancel_timer(self, mock_manager_class, mock_dbus_class):
    """Test cancelling a scheduled timer"""
    mock_dbus = MagicMock()
    mock_dbus_class.return_value.__enter__ = MagicMock(return_value=mock_dbus)
    mock_dbus_class.return_value.__exit__ = MagicMock(return_value=None)

    mock_manager = MagicMock()
    mock_manager.Manager.StopUnit = MagicMock()
    mock_manager_class.return_value = mock_manager

    manager = LinuxTimerManager(app_name="TestApp")
    manager.timers["test-id"] = "test-unit"

    manager.cancel_timer("test-id")

    assert "test-id" not in manager.timers

  def test_cancel_nonexistent_timer(self):
    """Test cancelling a timer that doesn't exist"""
    manager = LinuxTimerManager(app_name="TestApp")
    # Should not raise an exception
    manager.cancel_timer("nonexistent-id")


class TestLinuxConfigStorage:
  """Tests for LinuxConfigStorage"""

  def test_init_creates_config(self):
    """Test config initialization creates directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
      with patch("os_interfaces.linux.user_config_dir", return_value=tmpdir):
        config = LinuxConfigStorage(app_name="TestApp", config_name="test")
        assert config.config_dir == Path(tmpdir)
        assert config.config_file == Path(tmpdir) / "test.yaml"

  def test_set_and_get(self):
    """Test setting and getting config values"""
    with tempfile.TemporaryDirectory() as tmpdir:
      with patch("os_interfaces.linux.user_config_dir", return_value=tmpdir):
        config = LinuxConfigStorage(app_name="TestApp", config_name="test")

        config.set("setting1", "value1")
        config.set("setting2", 42)
        config.set("setting3", {"nested": "config"})

        assert config.get("setting1") == "value1"
        assert config.get("setting2") == 42
        assert config.get("setting3") == {"nested": "config"}
        assert config.get("nonexistent") is None
        assert config.get("nonexistent", "default") == "default"

  def test_load_and_save(self):
    """Test loading and saving entire config"""
    with tempfile.TemporaryDirectory() as tmpdir:
      with patch("os_interfaces.linux.user_config_dir", return_value=tmpdir):
        config = LinuxConfigStorage(app_name="TestApp", config_name="test")

        test_config = {
          "key1": "value1",
          "key2": 123,
          "key3": {"nested": "data"},
        }

        config.save(test_config)
        loaded = config.load()

        assert loaded == test_config

  def test_persistence(self):
    """Test that config persists across instances"""
    with tempfile.TemporaryDirectory() as tmpdir:
      with patch("os_interfaces.linux.user_config_dir", return_value=tmpdir):
        config1 = LinuxConfigStorage(app_name="TestApp", config_name="test")
        config1.set("persistent_setting", "persistent_value")

        # Create new instance
        config2 = LinuxConfigStorage(app_name="TestApp", config_name="test")
        assert config2.get("persistent_setting") == "persistent_value"

  def test_yaml_format(self):
    """Test that config is saved in YAML format"""
    with tempfile.TemporaryDirectory() as tmpdir:
      with patch("os_interfaces.linux.user_config_dir", return_value=tmpdir):
        config = LinuxConfigStorage(app_name="TestApp", config_name="test")

        test_data = {"key": "value", "number": 42}
        config.save(test_data)

        # Read file directly and verify it's valid YAML
        with open(config.config_file, "r") as f:
          loaded = yaml.safe_load(f)

        assert loaded == test_data

  def test_empty_config(self):
    """Test handling of empty config file"""
    with tempfile.TemporaryDirectory() as tmpdir:
      with patch("os_interfaces.linux.user_config_dir", return_value=tmpdir):
        config = LinuxConfigStorage(app_name="TestApp", config_name="test")

        # Create empty file
        config.config_file.touch()

        loaded = config.load()
        assert loaded == {}
