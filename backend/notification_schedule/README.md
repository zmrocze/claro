# Carlo Notification Scheduler

Systemd-based daily scheduler for Carlo notification preparation.

## Overview

This module installs systemd user units that run the
`carlo-schedule-notifications` command once per day. The scheduler consists of
two systemd units:

1. **claro-notification-scheduler.service** - A oneshot service that executes
   `carlo-schedule-notifications`
2. **claro-notification-scheduler.timer** - A timer that triggers the service
   daily

## Installation

Install and enable the scheduler:

```bash
uv run python -c "from backend.notification_schedule.installer import ensure_notification_scheduler_units_installed; ensure_notification_scheduler_units_installed()"
```

This will:

- Link unit files from the package into `~/.config/systemd/user/`
- Enable the timer (auto-start on login)
- Start the timer immediately

The installation is **idempotent** - safe to run multiple times.

## Verification

Check timer status:

```bash
systemctl --user status claro-notification-scheduler.timer
```

List scheduled timers:

```bash
systemctl --user list-timers
```

View service logs:

```bash
journalctl --user -u claro-notification-scheduler.service
```

Follow logs in real-time:

```bash
journalctl --user -u claro-notification-scheduler.service -f
```

## Customization

The unit files are templates with sensible defaults. To customize:

1. Locate the linked files:
   ```bash
   ls -l ~/.config/systemd/user/claro-notification-scheduler.*
   ```

2. Edit the service unit to:
   - Change `ExecStart` command and arguments (replace `PLACEHOLDER1`,
     `PLACEHOLDER2`)
   - Set `WorkingDirectory` if needed
   - Uncomment and configure `EnvironmentFile` for environment variables
   - Enable logging via `StandardOutput=journal` and `StandardError=journal`

3. Edit the timer unit to:
   - Change schedule: replace `OnCalendar=daily` with specific time like
     `OnCalendar=*-*-* 09:00:00`
   - Add randomization: uncomment `RandomizedDelaySec=1h`
   - Adjust timing accuracy: uncomment `AccuracySec=5m`

4. Reload systemd after editing:
   ```bash
   systemctl --user daemon-reload
   systemctl --user restart claro-notification-scheduler.timer
   ```

## Uninstallation

For testing and development, uninstall the scheduler:

```bash
uv run python -c "from backend.notification_schedule.installer import uninstall_scheduler_units; uninstall_scheduler_units()"
```

This stops the timer and disables auto-start. Unit files remain linked but
inactive.

To fully remove (optional):

```bash
rm ~/.config/systemd/user/claro-notification-scheduler.service
rm ~/.config/systemd/user/claro-notification-scheduler.timer
systemctl --user daemon-reload
```

## Architecture

- **User-level units**: No root/sudo required, runs in your user session
- **pystemd**: Python library for D-Bus communication with systemd
- **LinkUnitFiles**: Creates symlinks (not copies) so package updates propagate
  automatically
- **Persistent timer**: Missed schedules (e.g. system was off) run on next login

## Troubleshooting

**Timer not running:**

```bash
systemctl --user is-enabled claro-notification-scheduler.timer
systemctl --user is-active claro-notification-scheduler.timer
```

**Service failing:**

- Check logs: `journalctl --user -u claro-notification-scheduler.service`
- Verify `carlo-schedule-notifications` executable exists and is in PATH
- Expected failure if the executable hasn't been implemented yet

**Unit files not found:**

- Reinstall: run the installation command again
- Check package data is included: verify `pyproject.toml` has template files in
  `include`
