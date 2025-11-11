# Claro Notification Scheduler

Systemd-based notification scheduling for Claro.

## Overview

This module provides configuration parsing for notification schedules. The
actual scheduling is handled by the `os_interfaces` module which provides two
methods:

1. **`schedule_daily`** - Installs a persistent daily timer that runs
   notification scheduling logic once per day
2. **`schedule_timer`** - Creates one-shot timers for individual notifications
   at specific times or within time ranges

## Architecture

The notification system has two layers:

### Daily Scheduler (Persistent)

- Installed once when the app starts
- Creates systemd timer + service units in `~/.config/systemd/user/`
- Runs daily at a configured time
- Idempotent - safe to call multiple times

### One-shot Notification Timers

- Created dynamically by the daily scheduler
- Each notification gets its own systemd timer + service
- Supports specific times (`time`) or randomized time ranges (`TimeRange`)
- Uses `RandomizedDelaySec` for time range notifications

## Usage

```python
from datetime import time
from os_interfaces.linux import LinuxTimerManager
from os_interfaces.base import TimerConfig

# Initialize timer manager
timer_mgr = LinuxTimerManager(app_name="claro")

# Install daily scheduler (idempotent, call on app startup)
timer_mgr.schedule_daily(
    command="/usr/bin/claro-schedule-notifications",
    args=["--config", "/path/to/config.yaml"],
    run_time=time(9, 0)  # Run daily at 9 AM
)

# Schedule individual notifications (called by daily scheduler)
from backend.notification_schedule.config_parser import TimeRange

# Specific time notification
config1 = TimerConfig(
    timing=time(14, 30),
    command="/usr/bin/claro-notify",
    args=["--message", "Afternoon reminder"],
    name="afternoon"
)
timer_mgr.schedule_timer(config1)

# Time range notification (randomized within range)
config2 = TimerConfig(
    timing=TimeRange(from_time=time(9, 0), to_time=time(11, 0)),
    command="/usr/bin/claro-notify",
    args=["--message", "Morning reminder"],
    name="morning"
)
timer_mgr.schedule_timer(config2)
```

## Verification

Check daily scheduler status:

```bash
systemctl --user status claro-notification-scheduler.timer
```

List all scheduled timers (including one-shot notification timers):

```bash
systemctl --user list-timers
```

View logs for the daily scheduler:

```bash
journalctl --user -u claro-notification-scheduler.service
```

View logs for specific notification timers:

```bash
systemctl --user list-units 'claro-notification-*.timer'
journalctl --user -u 'claro-notification-*'
```

## Customization

Unit files are created in `~/.config/systemd/user/` and can be edited:

1. Locate the unit files:
   ```bash
   ls -l ~/.config/systemd/user/claro-*
   ```

2. Edit the daily scheduler:
   ```bash
   systemctl --user edit --full claro-notification-scheduler.service
   systemctl --user edit --full claro-notification-scheduler.timer
   ```

3. Common customizations:
   - Change daily run time: modify `OnCalendar=*-*-* HH:MM:00` in timer unit
   - Add environment variables: add `Environment=VAR=value` to service unit
   - Adjust command/args: modify `ExecStart=` in service unit

4. Reload after editing:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart claro-notification-scheduler.timer
   ```

## Uninstallation

To stop and disable the daily scheduler:

```bash
systemctl --user stop claro-notification-scheduler.timer
systemctl --user disable claro-notification-scheduler.timer
```

To fully remove all unit files:

```bash
rm ~/.config/systemd/user/claro-notification-*.service
rm ~/.config/systemd/user/claro-notification-*.timer
rm ~/.config/systemd/user/claro-*.service
rm ~/.config/systemd/user/claro-*.timer
systemctl --user daemon-reload
```

## Implementation Details

- **User-level units**: No root/sudo required, runs in your user session
- **pystemd**: Python library for D-Bus communication with systemd
- **Persistent timers**: Use `Persistent=true` so missed schedules run on next
  boot
- **Unit files**: Written directly to `~/.config/systemd/user/`, no symlinks
- **Unique naming**: One-shot timers include notification name + time + UUID to
  avoid conflicts
- **RandomizedDelaySec**: Used for time range notifications to spread load

## Troubleshooting

**Timer not running:**

```bash
systemctl --user is-enabled claro-notification-scheduler.timer
systemctl --user is-active claro-notification-scheduler.timer
```

**Service failing:**

- Check logs: `journalctl --user -u claro-notification-scheduler.service`
- Verify the command specified in `ExecStart` exists and is executable
- Check that all required arguments are properly formatted

**Unit files not found:**

- Reinstall: run the installation command again
- Check package data is included: verify `pyproject.toml` has template files in
  `include`
