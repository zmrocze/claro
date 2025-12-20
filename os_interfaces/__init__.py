"""OS interface module - platform-specific implementations

Since we build separate executables for each platform,
import the appropriate implementation directly in the main entry points:
- main_linux.py will import from os_interfaces.linux
- main_android.py will import from os_interfaces.android
"""

from .base import NotificationManager, TimerManager

__all__ = [
  "NotificationManager",
  "TimerManager",
]
