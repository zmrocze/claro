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
- **pyyaml**: YAML configuration file handling

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

#### 4. LinuxConfigStorage

Stores configuration in YAML format in the user config directory.

```python
from os_interfaces.linux import LinuxConfigStorage

# Create config storage
config = LinuxConfigStorage(app_name="MyApp", config_name="config")

# Set individual values
config.set("api_key", "secret123")
config.set("max_retries", 3)

# Get values with defaults
api_key = config.get("api_key")
timeout = config.get("timeout", default=30)

# Load/save entire config
all_config = config.load()
config.save({"key1": "value1", "key2": "value2"})
```

**Location:** `~/.config/claro/config.yaml` (on Linux)

**Features:**

- Human-readable YAML format
- Automatic directory creation
- Immediate persistence on write
- Default value support

### Directory Structure

The implementation uses `platformdirs` to follow XDG Base Directory
specification:

```
~/.config/claro/          # Configuration files (YAML)
├── config.yaml
└── custom_config.yaml

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
pytest test/test_os_interfaces_linux.py::TestLinuxConfigStorage -v

# Run with coverage
pytest test/test_os_interfaces_linux.py --cov=os_interfaces.linux
```

### Test Coverage

- ✅ Notification manager (with/without event loop)
- ✅ Timer scheduling (future/past times)
- ✅ Timer cancellation
- ✅ Persistent storage (set/get/delete)
- ✅ Config storage (YAML format)
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
    LinuxConfigStorage,
)
from datetime import datetime, timedelta

# Initialize components
notifier = LinuxNotificationManager(app_name="ReminderApp")
timer_mgr = LinuxTimerManager(app_name="ReminderApp")
config = LinuxConfigStorage(app_name="ReminderApp", config_name="config")

# Load user preferences
reminder_enabled = config.get("reminders_enabled", default=True)

if reminder_enabled:
    # Schedule reminder
    def send_reminder(data):
        notifier.create_notification(
            title="Reminder",
            body=data["message"]
        )
    
    reminder_time = datetime.now() + timedelta(hours=1)
    timer_id = timer_mgr.schedule_timer(
        time=reminder_time,
        callback=send_reminder,
        data={"message": "Time for your meeting!"}
    )
    
    # Save timer ID for later cancellation
    config.set("active_timer_id", timer_id)
```

### Shared Code Pattern

Both `PersistentStorage` and `ConfigStorage` share similar patterns but differ
in:

1. **File Location**: Data dir vs Config dir (via `platformdirs`)
2. **Serialization**: Pickle (binary) vs YAML (text)
3. **Use Case**: Runtime data vs User configuration

This design allows for:

- Clear separation of concerns
- Appropriate storage format for each use case
- Following platform conventions

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
