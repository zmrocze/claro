# OS Interfaces

Platform-specific implementations for notifications, timers, and storage.

## Architecture

The OS interfaces follow a clean architecture pattern:

1. **Abstract Base Classes** (`base.py`): Define the interface contracts
2. **Platform Implementations** (`linux.py`, `android.py`): Implement
   platform-specific behavior

Constructors accept required parameters directly - no complex factory patterns
needed.

## Linux Implementation

### Dependencies

- **platformdirs**: Cross-platform directory paths (config, data, cache)
- **desktop-notifier**: Native desktop notifications via D-Bus
- **pystemd**: Python bindings for systemd (transient timer units)

### Components

#### 1. LinuxNotificationManager

Uses `desktop-notifier` to send native desktop notifications via D-Bus.

```python
from os_interfaces.linux import LinuxNotificationManager

# Create notification manager
notifier = LinuxNotificationManager(app_name="MyApp")

# Send notification
notifier.create_notification(
    title="Hello",
    body="This is a notification"
)

# Send notification with click callback
def handle_click():
    print("Notification clicked!")

notifier.create_notification(
    title="Interactive",
    body="Click me!",
    on_clicked=handle_click
)
```

**Features:**

- Async/sync event loop handling
- Native Linux desktop notifications
- Automatic D-Bus integration

#### 2. LinuxTimerManager

Uses `pystemd` to create systemd transient timer units for scheduling.

```python
from os_interfaces.linux import LinuxTimerManager
from datetime import datetime, timedelta

# Create timer manager
timer_mgr = LinuxTimerManager(app_name="MyApp")

# Schedule a timer
def my_callback(data=None):
    print(f"Timer triggered! Data: {data}")

future_time = datetime.now() + timedelta(minutes=5)
timer_id = timer_mgr.schedule_timer(
    time=future_time,
    callback=my_callback,
    data={"reminder": "Take a break"}
)

# Cancel timer
timer_mgr.cancel_timer(timer_id)
```

**Features:**

- Systemd transient units (no persistent files)
- User-mode timers (no root required)
- Automatic cleanup on cancellation
- Fallback execution for past times

**Current Limitations:**

- Timer creates a systemd timer unit but without an associated service unit
- Callbacks are stored in memory but not executed by systemd
- For production use, implement IPC mechanism (D-Bus signals, Unix sockets, or
  HTTP webhooks) to trigger callbacks when timer fires

#### 3. LinuxPersistentStorage

Stores Python objects using pickle in the user data directory.

```python
from os_interfaces.linux import LinuxPersistentStorage

# Create storage
storage = LinuxPersistentStorage(app_name="MyApp", storage_name="session")

# Store data
storage.set("user_id", "12345")
storage.set("preferences", {"theme": "dark", "lang": "en"})

# Retrieve data
user_id = storage.get("user_id")
prefs = storage.get("preferences")

# Delete data
storage.delete("user_id")
```

**Location:** `~/.local/share/claro/session.pkl` (on Linux)

**Features:**

- Automatic directory creation
- Pickle serialization (supports complex Python objects)
- Immediate persistence on write
- Isolated storage per storage_name

### Directory Structure

The implementation uses `platformdirs` to follow XDG Base Directory
specification:

```
~/.local/share/claro/     # Application data (pickle)
├── storage.pkl
├── session.pkl
└── checkpoint.pkl
```

## Testing

Comprehensive test suite with mocking for external dependencies:

```bash
# Run all tests
pytest test/test_os_interfaces_linux.py -v

# Run specific test class
pytest test/test_os_interfaces_linux.py -k PersistentStorage -v

# Run with coverage
pytest test/test_os_interfaces_linux.py --cov=os_interfaces.linux
```

### Test Coverage

- ✅ Notification manager (with/without event loop)
- ✅ Timer scheduling (future/past times)
- ✅ Timer cancellation
- ✅ Persistent storage (set/get/delete)
- ✅ Data persistence across instances
- ✅ Storage isolation
- ✅ Factory functions
- ✅ Integration scenarios

## Usage Examples

### Complete Example: Reminder System

```python
from os_interfaces.linux import (
    LinuxNotificationManager,
    LinuxTimerManager,
)
from datetime import datetime, timedelta

# Initialize components
notifier = LinuxNotificationManager(app_name="ReminderApp")
timer_mgr = LinuxTimerManager(app_name="ReminderApp")

# Schedule reminder
reminder_time = datetime.now() + timedelta(hours=1)
timer_id = timer_mgr.schedule_timer(
    timer_config=TimerConfig(
        timing=reminder_time,
        command="/usr/bin/echo",
        args=["Time for your meeting!"],
        name="meeting-reminder",
    )
)
```

### Shared Code Pattern

Persistent storage uses platform-appropriate data directories (via
`platformdirs`).

## Platform Support

Currently implemented:

- ✅ Linux (desktop-notifier, pystemd, platformdirs)

Planned:

- 🚧 Android (pyjnius, Android APIs)
- 🚧 macOS (NSUserNotification, launchd)
- 🚧 Windows (win10toast, Task Scheduler)

## Notes

### Systemd Timer Limitations

The current timer implementation uses systemd transient units, which:

- Require systemd (most modern Linux distros)
- Run in user mode (no root needed)
- Are temporary (don't survive reboot)
- Execute shell commands (callback mechanism needs IPC)

For production use, consider implementing a callback mechanism via:

- D-Bus signals
- Unix sockets
- HTTP webhook to the app

### Desktop Notifier Event Loop

`desktop-notifier` is async-first. The implementation handles both:

- Running event loop: Uses `asyncio.create_task()`
- No event loop: Uses `loop.run_until_complete()`

For best results, integrate with your app's event loop.

## Contributing

When adding new platform implementations:

1. Inherit from base classes in `base.py`
2. Follow the constructor/factory pattern
3. Add comprehensive tests
4. Document platform-specific requirements
5. Update this README
