# Claro Notification Scheduler

Systemd-based notification scheduling for Claro.

## Overview

This module provides:

1. **Configuration parsing** - Parse YAML config files with notification rules
2. **Scheduler program** - `claro-notification-scheduler` reads config and
   schedules notifications for the next day
3. **OS integration** - Uses `os_interfaces` module for systemd timer management

The `os_interfaces` module provides two key methods:

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

## Scheduler Program Usage

The `claro-notification-scheduler` program reads the notification configuration
and schedules all notifications for the next day.

### Command Line

```bash
# Use default config location (~/.config/claro/notification_schedule.yaml)
claro-notification-scheduler

# Specify custom config file
claro-notification-scheduler --config /path/to/config.yaml

# Specify custom notification command (default: claro-notification)
claro-notification-scheduler --notification-command /path/to/custom-notifier
```

### Configuration File Format

Create `~/.config/claro/notification_schedule.yaml`:

```yaml
morning_reflection:
  hour: "08:30" # Specific time
  calling: |
    Good morning! How are you feeling today?
  frequency: 1.0 # Always schedule

afternoon_checkin:
  hours_range: # Random time within range
    from: "14:00"
    to: "16:00"
  calling: |
    Time for an afternoon check-in!
  frequency: 0.8 # 80% chance to schedule

hydration_reminder:
  hours_range:
    from: "09:00"
    to: "17:00"
  calling: |
    Remember to drink water!
  frequency: 3.0 # Schedule 3 times
```

### Frequency Semantics

- **frequency < 1**: Probabilistic scheduling. Random draw determines if
  notification is scheduled.
  - `0.8` = 80% chance to schedule once
  - `0.5` = 50% chance to schedule once
  - `0.0` = Never schedule

- **frequency >= 1**: Schedule floor(frequency) or ceil(frequency) times based
  on fractional part.
  - `1.0` = Schedule once (always)
  - `1.5` = 50% chance of 1 schedule, 50% chance of 2 schedules
  - `2.0` = Schedule twice (creates `name-0` and `name-1`)
  - `2.3` = 70% chance of 2 schedules, 30% chance of 3 schedules
  - `3.0` = Schedule three times

### Building with Nix

```bash
# Build the scheduler
nix build .#claro-notification-scheduler

# Run directly
./result/bin/claro-notification-scheduler
```

## Programmatic Usage

```python
from datetime import time
from os_interfaces.linux import LinuxTimerManager
from os_interfaces.base import TimerConfig
from notification_schedule.config_parser import TimeRange

# Initialize timer manager
timer_mgr = LinuxTimerManager(app_name="claro")

# Schedule individual notifications
config = TimerConfig(
    timing=time(14, 30),  # or TimeRange(from_time=..., to_time=...)
    command="claro-notification",
    args=["afternoon_checkin"],  # notification name
    name="afternoon_checkin"
)
timer_mgr.schedule_timer(config)
```

## Verification

Check daily scheduler status:

```bash
systemctl --user status claro-claro-notification-scheduler.timer
```

List all scheduled timers (including one-shot notification timers):

```bash
systemctl --user list-timers
```

View logs for the daily scheduler:

```bash
journalctl --user -u claro-claro-notification-scheduler.service
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
   systemctl --user edit --full claro-claro-notification-scheduler.service
   systemctl --user edit --full claro-claro-notification-scheduler.timer
   ```

3. Common customizations:
   - Change daily run time: modify `OnCalendar=*-*-* HH:MM:00` in timer unit
   - Add environment variables: add `Environment=VAR=value` to service unit
   - Adjust command/args: modify `ExecStart=` in service unit

4. Reload after editing:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart claro-claro-notification-scheduler.timer
   ```

## Uninstallation

To stop and disable the daily scheduler:

```bash
systemctl --user stop claro-claro-notification-scheduler.timer
systemctl --user disable claro-claro-notification-scheduler.timer
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
systemctl --user is-enabled claro-claro-notification-scheduler.timer
systemctl --user is-active claro-claro-notification-scheduler.timer
```

**Service failing:**

- Check logs: `journalctl --user -u claro-claro-notification-scheduler.service`
- Verify the command specified in `ExecStart` exists and is executable
- Check that all required arguments are properly formatted

**Unit files not found:**

- Reinstall: run the installation command again
- Check package data is included: verify `pyproject.toml` has template files in
  `include`
