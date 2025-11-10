"""
Test notification scheduling configuration parser
Run with: uv run pytest test/test_notification_scheduling.py
"""

import pytest
from datetime import time
from pydantic import ValidationError

from backend.notification_schedule import (
  NotificationConfig,
  NotificationScheduleConfig,
  TimeRange,
  parse_notification_config,
)


@pytest.fixture
def valid_config_yaml():
  """Fixture providing valid YAML configuration content"""
  return """
morning_reflection:
  hours_range:
    from: "08:00"
    to: "10:00"
  calling: |
    Good morning! How are you feeling today?
    Let's take a moment to reflect on your goals for the day.
  frequency: 1.0

afternoon_checkin:
  hour: "14:30"
  calling: |
    Time for an afternoon check-in!
    How is your day going so far?
  frequency: 0.8

evening_gratitude:
  hours_range:
    from: "19:00"
    to: "21:00"
  calling: |
    As the day winds down, let's practice gratitude.
    What are three things you're grateful for today?
  frequency: 1.0
"""


@pytest.fixture
def invalid_config_both_time_fields():
  """Fixture with invalid config - both hour and hours_range specified"""
  return """
invalid_notification:
  hours_range:
    from: "08:00"
    to: "10:00"
  hour: "09:00"
  calling: "This should fail"
  frequency: 1.0
"""


@pytest.fixture
def invalid_config_no_time_fields():
  """Fixture with invalid config - neither hour nor hours_range specified"""
  return """
invalid_notification:
  calling: "This should fail"
  frequency: 1.0
"""


@pytest.fixture
def invalid_config_bad_time_range():
  """Fixture with invalid config - from_time after to_time"""
  return """
invalid_notification:
  hours_range:
    from: "10:00"
    to: "08:00"
  calling: "This should fail"
  frequency: 1.0
"""


@pytest.fixture
def invalid_config_bad_frequency():
  """Fixture with invalid config - frequency out of range"""
  return """
invalid_notification:
  hour: "09:00"
  calling: "This should fail"
  frequency: 1.5
"""


def test_parse_valid_config(valid_config_yaml, tmp_path):
  """Test parsing a valid configuration file"""
  config_file = tmp_path / "config.yaml"
  config_file.write_text(valid_config_yaml)

  config = parse_notification_config(config_file)

  assert isinstance(config, NotificationScheduleConfig)
  assert len(config.notifications) == 3
  assert "morning_reflection" in config.notifications
  assert "afternoon_checkin" in config.notifications
  assert "evening_gratitude" in config.notifications


def test_notification_with_hours_range(valid_config_yaml, tmp_path):
  """Test notification configured with hours_range"""
  config_file = tmp_path / "config.yaml"
  config_file.write_text(valid_config_yaml)

  config = parse_notification_config(config_file)
  morning = config.notifications["morning_reflection"]

  assert isinstance(morning.timing, TimeRange)
  assert morning.timing.from_time == time(8, 0)
  assert morning.timing.to_time == time(10, 0)
  assert morning.frequency == 1.0
  assert "Good morning" in morning.calling


def test_notification_with_exact_hour(valid_config_yaml, tmp_path):
  """Test notification configured with exact hour"""
  config_file = tmp_path / "config.yaml"
  config_file.write_text(valid_config_yaml)

  config = parse_notification_config(config_file)
  afternoon = config.notifications["afternoon_checkin"]

  assert isinstance(afternoon.timing, time)
  assert afternoon.timing == time(14, 30)
  assert afternoon.frequency == 0.8
  assert "afternoon check-in" in afternoon.calling


def test_invalid_both_time_fields(invalid_config_both_time_fields, tmp_path):
  """Test that specifying both hour and hours_range raises ValueError"""
  config_file = tmp_path / "config.yaml"
  config_file.write_text(invalid_config_both_time_fields)

  # Should raise ValueError during YAML transformation
  with pytest.raises(ValueError, match="both 'hour' and 'hours_range' specified"):
    parse_notification_config(config_file)


def test_invalid_no_time_fields(invalid_config_no_time_fields, tmp_path):
  """Test that specifying neither hour nor hours_range nor timing raises ValidationError"""
  config_file = tmp_path / "config.yaml"
  config_file.write_text(invalid_config_no_time_fields)

  # Should fail because timing field is required
  with pytest.raises(ValidationError):
    parse_notification_config(config_file)


def test_invalid_time_range(invalid_config_bad_time_range, tmp_path):
  """Test that from_time >= to_time raises ValidationError"""
  config_file = tmp_path / "config.yaml"
  config_file.write_text(invalid_config_bad_time_range)

  with pytest.raises(ValidationError, match="must be before"):
    parse_notification_config(config_file)


def test_invalid_frequency(invalid_config_bad_frequency, tmp_path):
  """Test that frequency outside [0, 1] raises ValidationError"""
  config_file = tmp_path / "config.yaml"
  config_file.write_text(invalid_config_bad_frequency)

  with pytest.raises(ValidationError, match="between 0 and 1"):
    parse_notification_config(config_file)


def test_file_not_found():
  """Test that missing config file raises FileNotFoundError"""
  with pytest.raises(FileNotFoundError):
    parse_notification_config("/nonexistent/path/config.yaml")


def test_time_range_model():
  """Test TimeRange model directly"""
  time_range = TimeRange(from_time="08:00", to_time="10:00")  # type: ignore[arg-type]

  assert time_range.from_time == time(8, 0)
  assert time_range.to_time == time(10, 0)


def test_notification_config_model():
  """Test NotificationConfig model directly"""
  # Test with time string
  config1 = NotificationConfig(
    timing="14:30",  # type: ignore[arg-type]
    calling="Test notification",
    frequency=0.5,
  )
  assert isinstance(config1.timing, time)
  assert config1.timing == time(14, 30)
  assert config1.calling == "Test notification"
  assert config1.frequency == 0.5

  # Test with TimeRange
  config2 = NotificationConfig(
    timing=TimeRange(from_time="09:00", to_time="17:00"),  # type: ignore[arg-type]
    calling="Test notification",
    frequency=0.8,
  )
  assert isinstance(config2.timing, TimeRange)
  assert config2.timing.from_time == time(9, 0)
  assert config2.timing.to_time == time(17, 0)


def test_multiline_calling_text(tmp_path):
  """Test that multiline calling text is preserved"""
  yaml_content = """
test_notification:
  hour: "09:00"
  calling: |
    Line 1
    Line 2
    Line 3
  frequency: 1.0
"""
  config_file = tmp_path / "config.yaml"
  config_file.write_text(yaml_content)

  config = parse_notification_config(config_file)
  notification = config.notifications["test_notification"]

  assert "Line 1" in notification.calling
  assert "Line 2" in notification.calling
  assert "Line 3" in notification.calling


def test_roundtrip_serialization(valid_config_yaml, tmp_path):
  """Test that config can be parsed, serialized, and parsed again with same result"""
  import yaml

  # Parse original config
  config_file = tmp_path / "config.yaml"
  config_file.write_text(valid_config_yaml)
  config1 = parse_notification_config(config_file)

  # Serialize to dict and back to YAML
  config_dict = {}
  for name, notif in config1.notifications.items():
    match notif.timing:
      case TimeRange():
        config_dict[name] = {
          "hours_range": {
            "from": notif.timing.from_time.strftime("%H:%M"),
            "to": notif.timing.to_time.strftime("%H:%M"),
          },
          "calling": notif.calling,
          "frequency": notif.frequency,
        }
      case time():
        config_dict[name] = {
          "hour": notif.timing.strftime("%H:%M"),
          "calling": notif.calling,
          "frequency": notif.frequency,
        }

  # Write serialized config to new file
  roundtrip_file = tmp_path / "roundtrip.yaml"
  with open(roundtrip_file, "w") as f:
    yaml.dump(config_dict, f)

  # Parse the roundtrip config
  config2 = parse_notification_config(roundtrip_file)

  # Verify both configs are equivalent
  assert len(config1.notifications) == len(config2.notifications)

  for name in config1.notifications:
    notif1 = config1.notifications[name]
    notif2 = config2.notifications[name]

    assert notif1.calling == notif2.calling
    assert notif1.frequency == notif2.frequency

    match (notif1.timing, notif2.timing):
      case (TimeRange(), TimeRange()):
        assert notif1.timing.from_time == notif2.timing.from_time
        assert notif1.timing.to_time == notif2.timing.to_time
      case (time(), time()):
        assert notif1.timing == notif2.timing
      case _:
        raise AssertionError(
          f"Type mismatch: {type(notif1.timing)} vs {type(notif2.timing)}"
        )
