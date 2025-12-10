"""
Notification scheduling configuration parser
Parses YAML config files with notification scheduling rules
"""

from typing import Dict
from pathlib import Path
from datetime import time
import yaml
from pydantic import BaseModel, field_validator, model_validator


class TimeRange(BaseModel):
  """Time range for notification scheduling (time-of-day only, no date)"""

  from_time: time
  to_time: time

  @field_validator("from_time", "to_time", mode="before")
  @classmethod
  def parse_time(cls, v: str) -> time:
    """Parse time string in HH:MM format"""
    if isinstance(v, time):
      return v
    try:
      hours, minutes = v.split(":")
      return time(int(hours), int(minutes))
    except (ValueError, AttributeError) as e:
      raise ValueError(f"Time must be in HH:MM format, got: {v}") from e

  @model_validator(mode="after")
  def validate_time_range(self):
    """Ensure from_time is before to_time"""
    if self.from_time >= self.to_time:
      raise ValueError(
        f"from_time ({self.from_time}) must be before to_time ({self.to_time})"
      )
    return self


class NotificationConfig(BaseModel):
  """Configuration for a single notification"""

  timing: TimeRange | time
  calling: str
  frequency: float

  @field_validator("timing", mode="before")
  @classmethod
  def parse_timing(cls, v):
    """Parse timing field - handles time strings, TimeRange objects, and TimeRange dicts"""
    match v:
      case time() | TimeRange():
        return v
      case str():
        hours, minutes = v.split(":")
        return time(int(hours), int(minutes))
      case dict():
        return TimeRange(**v)
      case _:
        return v

  @field_validator("frequency")
  @classmethod
  def validate_frequency(cls, v: float) -> float:
    """Validate frequency value.

    - 0 <= frequency < 1: probabilistic scheduling
    - frequency >= 1: schedule floor or ceil times based on fractional part
      (e.g., 1.5 = 50% chance of 1, 50% chance of 2)
    """
    if v < 0:
      raise ValueError(f"Frequency must be non-negative, got: {v}")
    return v


class NotificationScheduleConfig(BaseModel):
  """Complete notification schedule configuration"""

  notifications: Dict[str, NotificationConfig]


def parse_notification_config(config_path: Path | str) -> NotificationScheduleConfig:
  """
  Parse notification scheduling configuration from YAML file

  Args:
      config_path: Path to the YAML configuration file

  Returns:
      NotificationScheduleConfig with parsed notification rules

  Raises:
      FileNotFoundError: If config file doesn't exist
      yaml.YAMLError: If YAML is malformed
      pydantic.ValidationError: If config doesn't match schema
  """
  config_path = Path(config_path)

  if not config_path.exists():
    raise FileNotFoundError(f"Configuration file not found: {config_path}")

  with open(config_path, "r") as f:
    raw_config = yaml.safe_load(f)

  # Transform the YAML structure to use timing field
  notifications = {}
  for name, config in raw_config.items():
    # Validate that both hour and hours_range are not specified
    if "hour" in config and "hours_range" in config:
      raise ValueError(
        f"Notification '{name}': both 'hour' and 'hours_range' specified. "
        "Only one timing field is allowed."
      )

    # Transform hours_range or hour into timing field
    match config:
      case {"hours_range": hours_range_data, **rest}:
        config = {
          **rest,
          "timing": TimeRange(
            from_time=hours_range_data["from"], to_time=hours_range_data["to"]
          ),
        }
      case {"hour": hour_value, **rest}:
        config = {**rest, "timing": hour_value}
      case _:
        pass  # timing already in correct format

    notifications[name] = NotificationConfig(**config)

  return NotificationScheduleConfig(notifications=notifications)
