"""Android-specific implementations of OS interfaces."""

from __future__ import annotations

import logging
import os
import random
import threading
from datetime import datetime, time
from pathlib import Path
from typing import Any, Callable, Optional

from android.runnable import run_on_ui_thread  # type: ignore
from jnius import PythonJavaClass, autoclass, java_method  # type: ignore

from .base import (
  ManageKeys,
  NotificationManager,
  ScheduleTimeRange,
  TimerConfig,
  TimerManager,
)

logger = logging.getLogger(__name__)

# --- PyJNIus handles ---
PythonActivity = autoclass("org.kivy.android.PythonActivity")
Intent = autoclass("android.content.Intent")
IntentFilter = autoclass("android.content.IntentFilter")
PendingIntent = autoclass("android.app.PendingIntent")
AlertDialogBuilder = autoclass("android.app.AlertDialog$Builder")
NotificationManagerJava = autoclass("android.app.NotificationManager")
NotificationChannel = autoclass("android.app.NotificationChannel")
BuildVersion = autoclass("android.os.Build$VERSION")
NotificationCompatBuilder = autoclass("androidx.core.app.NotificationCompat$Builder")
NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
AlarmManagerJava = autoclass("android.app.AlarmManager")
Calendar = autoclass("java.util.Calendar")
AndroidRDrawable = autoclass("android.R$drawable")
Context = autoclass("android.content.Context")
EditText = autoclass("android.widget.EditText")
InputType = autoclass("android.text.InputType")
PasswordTransformationMethod = autoclass(
  "android.text.method.PasswordTransformationMethod"
)

ACTION_CLICK = "com.claro.NOTIFICATION_CLICKED"
ACTION_DISMISS = "com.claro.NOTIFICATION_DISMISSED"
CHANNEL_ID = "claro-general"

SERVICE_SCHEDULER = "org.claro.claro.ServiceScheduler"
SERVICE_NOTIFIER = "org.claro.claro.ServiceNotifier"
ComponentName = autoclass("android.content.ComponentName")


def _context():
  activity = PythonActivity.mActivity
  if activity is not None:
    return activity.getApplicationContext()
  return autoclass("org.kivy.android.PythonService").mService.getApplicationContext()


def setup_android_env() -> None:
  """Set CLARO_DOTENV_PATH for Android. Call before importing backend modules."""
  try:
    from android.storage import app_storage_path  # type: ignore

    env_file = Path(app_storage_path()) / "app" / "builds" / "android" / ".env.android"
  except Exception:
    env_file = Path(
      "/data/user/0/org.claro.claro/files/app/builds/android/.env.android"
    )
  if env_file.exists():
    os.environ["CLARO_DOTENV_PATH"] = str(env_file)


def _android_config_path() -> Path:
  """Return the notification schedule config path on Android."""
  try:
    from android.storage import app_storage_path  # type: ignore

    return Path(app_storage_path()) / "notification_schedule.yaml"
  except Exception:
    return Path("/data/user/0/org.claro.claro/files/notification_schedule.yaml")


def _flags(base: int | None = None) -> int:
  flag_immutable = PendingIntent.FLAG_IMMUTABLE
  flag_update = PendingIntent.FLAG_UPDATE_CURRENT
  return (base or 0) | flag_immutable | flag_update


def _ensure_channel(ctx, manager) -> None:
  if BuildVersion.SDK_INT < 26:
    return
  channel = NotificationChannel(
    CHANNEL_ID,
    "Claro",
    NotificationManagerJava.IMPORTANCE_DEFAULT,
  )
  manager.createNotificationChannel(channel)


class _NotificationReceiver(PythonJavaClass):
  __javainterfaces__ = ["android/content/BroadcastReceiver"]
  __javacontext__ = "app"

  def __init__(self, on_clicked: Optional[Callable], on_dismissed: Optional[Callable]):
    super().__init__()
    self.on_clicked = on_clicked
    self.on_dismissed = on_dismissed

  @java_method("(Landroid/content/Context;Landroid/content/Intent;)V")
  def onReceive(self, _context, intent):
    try:
      action = intent.getAction()
      if action == ACTION_CLICK and self.on_clicked:
        self.on_clicked()
      elif action == ACTION_DISMISS and self.on_dismissed:
        self.on_dismissed()
    except Exception:  # pragma: no cover - defensive
      logger.exception("Notification callback failed")


def _service_intent(ctx, service_class: str, argument: str = "") -> Any:
  """Create an Intent targeting a p4a foreground service."""
  intent = Intent()
  intent.setComponent(ComponentName(ctx.getPackageName(), service_class))
  intent.putExtra("pythonServiceArgument", argument)
  intent.putExtra("serviceTitle", "Claro")
  intent.putExtra("serviceDescription", "Running scheduled task")
  return intent


def _rand_request_code() -> int:
  return random.randint(10_000, 99_999)


def _millis(dt: datetime) -> int:
  return int(dt.timestamp() * 1000)


def _pick_datetime(timing: datetime | ScheduleTimeRange) -> datetime:
  if isinstance(timing, ScheduleTimeRange):
    span = timing.to_time - timing.from_time
    return timing.from_time + span * random.random()
  return timing


def _encrypted_prefs(ctx, service_name: str):
  MasterKeyBuilder = autoclass("androidx.security.crypto.MasterKey$Builder")
  MasterKeyKeyScheme = autoclass("androidx.security.crypto.MasterKey$KeyScheme")
  EncryptedSharedPreferences = autoclass(
    "androidx.security.crypto.EncryptedSharedPreferences"
  )
  PrefKeyEncryptionScheme = autoclass(
    "androidx.security.crypto.EncryptedSharedPreferences$PrefKeyEncryptionScheme"
  )
  PrefValueEncryptionScheme = autoclass(
    "androidx.security.crypto.EncryptedSharedPreferences$PrefValueEncryptionScheme"
  )
  master_key = MasterKeyBuilder(ctx).setKeyScheme(MasterKeyKeyScheme.AES256_GCM).build()
  return EncryptedSharedPreferences.create(
    ctx,
    service_name,
    master_key,
    PrefKeyEncryptionScheme.AES256_SIV,
    PrefValueEncryptionScheme.AES256_GCM,
  )


class _DialogClickListener(PythonJavaClass):
  __javainterfaces__ = ["android/content/DialogInterface$OnClickListener"]
  __javacontext__ = "app"

  def __init__(self, callback: Callable):
    super().__init__()
    self.callback = callback

  @java_method("(Landroid/content/DialogInterface;I)V")
  def onClick(self, dialog, which):
    self.callback(dialog, which)


class _DialogCancelListener(PythonJavaClass):
  __javainterfaces__ = ["android/content/DialogInterface$OnCancelListener"]
  __javacontext__ = "app"

  def __init__(self, callback: Callable[[], None]):
    super().__init__()
    self.callback = callback

  @java_method("(Landroid/content/DialogInterface;)V")
  def onCancel(self, _dialog):
    self.callback()


class AndroidManageKeys(ManageKeys):
  def __init__(self, service_name: str):
    self.ctx = _context()
    self.activity = PythonActivity.mActivity
    self.service_name = service_name

  def _prefs(self):
    return _encrypted_prefs(self.ctx, self.service_name)

  def get_key(self, key_name: str) -> Optional[str]:
    try:
      value = self._prefs().getString(key_name, None)
      return value if value else None
    except Exception as e:
      logger.warning(
        "Failed to retrieve '%s' from Android secure storage: %s", key_name, e
      )
      return None

  def set_key(self, key_name: str, value: str) -> None:
    try:
      editor = self._prefs().edit()
      editor.putString(key_name, value)
      if not editor.commit():
        raise RuntimeError(f"Failed to store '{key_name}' in Android secure storage")
      logger.info("API key '%s' stored successfully", key_name)
    except Exception as e:
      logger.error("Failed to store API key '%s': %s", key_name, e)
      raise

  def prompt_for_key(
    self,
    key_name: str,
    *,
    description: Optional[str] = None,
    prompt_label: Optional[str] = None,
  ) -> Optional[str]:
    done = threading.Event()
    result: dict[str, Optional[str]] = {"value": None}
    refs: dict[str, Any] = {}

    def finish(value: Optional[str]) -> None:
      result["value"] = value.strip() if value else None
      done.set()

    @run_on_ui_thread
    def show_prompt() -> None:
      try:
        input_field = EditText(self.activity)
        input_field.setInputType(
          InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD
        )
        input_field.setTransformationMethod(PasswordTransformationMethod.getInstance())
        input_field.setSingleLine(True)
        input_field.setHint(prompt_label or key_name)
        builder = AlertDialogBuilder(self.activity)
        builder.setTitle(prompt_label or key_name)
        if description:
          builder.setMessage(description)
        builder.setView(input_field)
        refs["positive"] = _DialogClickListener(
          lambda _dialog, _which: finish(str(input_field.getText().toString()))
        )
        refs["negative"] = _DialogClickListener(lambda _dialog, _which: finish(None))
        refs["cancel"] = _DialogCancelListener(lambda: finish(None))
        dialog = (
          builder.setPositiveButton("Save", refs["positive"])
          .setNegativeButton("Cancel", refs["negative"])
          .create()
        )
        dialog.setOnCancelListener(refs["cancel"])
        dialog.show()
      except Exception:
        logger.exception("Failed to show Android key prompt")
        done.set()

    show_prompt()
    done.wait()
    return result["value"]


class AndroidNotificationManager(NotificationManager):
  """Android notification manager using PyJNIus NotificationCompat."""

  def __init__(self, app_name: str | None = None):
    self.ctx = _context()
    self.manager = self.ctx.getSystemService(Context.NOTIFICATION_SERVICE)
    _ensure_channel(self.ctx, self.manager)

  async def create_notification(
    self,
    title: str,
    body: str,
    on_clicked: Optional[Callable] = None,
    on_dismissed: Optional[Callable] = None,
  ) -> None:
    receiver = _NotificationReceiver(on_clicked, on_dismissed)
    f = IntentFilter()
    f.addAction(ACTION_CLICK)
    f.addAction(ACTION_DISMISS)
    self.ctx.registerReceiver(receiver, f)

    notification_id = _rand_request_code()
    icon = self.ctx.getApplicationInfo().icon or AndroidRDrawable.ic_dialog_info

    click_intent = Intent(self.ctx, PythonActivity)
    click_intent.setAction(ACTION_CLICK)
    click_intent.putExtra("notification_id", notification_id)
    click_pi = PendingIntent.getBroadcast(
      self.ctx, notification_id, click_intent, _flags()
    )

    dismiss_intent = Intent(self.ctx, PythonActivity)
    dismiss_intent.setAction(ACTION_DISMISS)
    dismiss_intent.putExtra("notification_id", notification_id)
    dismiss_pi = PendingIntent.getBroadcast(
      self.ctx, notification_id + 1, dismiss_intent, _flags()
    )

    builder = (
      NotificationCompatBuilder(self.ctx, CHANNEL_ID)
      .setSmallIcon(icon)
      .setContentTitle(title)
      .setContentText(body)
      .setAutoCancel(True)
      .setPriority(NotificationCompat.PRIORITY_DEFAULT)
      .setDefaults(NotificationCompat.DEFAULT_ALL)
      .setContentIntent(click_pi)
      .setDeleteIntent(dismiss_pi)
    )

    self.manager.notify(notification_id, builder.build())
    logger.info("Notification %s created", notification_id)


class AndroidTimerManager(TimerManager):
  """Android timer manager using AlarmManager + p4a foreground services."""

  def __init__(self, app_name: str | None = None):
    self.ctx = _context()
    self.alarm_manager = self.ctx.getSystemService(Context.ALARM_SERVICE)

  def _schedule_alarm(self, intent: Any, request_code: int, trigger_ms: int) -> None:
    pi = PendingIntent.getForegroundService(self.ctx, request_code, intent, _flags())
    if BuildVersion.SDK_INT >= 23:
      self.alarm_manager.setExactAndAllowWhileIdle(
        AlarmManagerJava.RTC_WAKEUP, trigger_ms, pi
      )
    else:
      self.alarm_manager.setExact(AlarmManagerJava.RTC_WAKEUP, trigger_ms, pi)

  def schedule_timer(self, timer_config: TimerConfig, appconfig: Any = None) -> str:
    target = _pick_datetime(timer_config.timing)
    trigger_at = max(_millis(target), _millis(datetime.now()) + 1000)
    notification_name = timer_config.args[0] if timer_config.args else ""
    intent = _service_intent(self.ctx, SERVICE_NOTIFIER, notification_name)
    request_code = _rand_request_code()
    self._schedule_alarm(intent, request_code, trigger_at)
    timer_id = f"alarm-{request_code}"
    logger.info("Scheduled notifier service %s at %s", timer_id, target.isoformat())
    return timer_id

  def schedule_daily(
    self, command: str, args: list[str], run_time: time, appconfig: Any = None
  ) -> None:
    now_ms = _millis(datetime.now())
    cal = Calendar.getInstance()
    cal.set(Calendar.HOUR_OF_DAY, run_time.hour)
    cal.set(Calendar.MINUTE, run_time.minute)
    cal.set(Calendar.SECOND, 0)
    cal.set(Calendar.MILLISECOND, 0)
    first_fire = cal.getTimeInMillis()
    if first_fire <= now_ms:
      cal.add(Calendar.DATE, 1)
      first_fire = cal.getTimeInMillis()

    intent = _service_intent(self.ctx, SERVICE_SCHEDULER)
    pi = PendingIntent.getForegroundService(self.ctx, 42_000, intent, _flags())
    self.alarm_manager.setRepeating(
      AlarmManagerJava.RTC_WAKEUP,
      first_fire,
      AlarmManagerJava.INTERVAL_DAY,
      pi,
    )
    logger.info("Scheduled daily scheduler service for %s", run_time.isoformat())

  def cancel_timer(self, timer_id: str) -> None:
    raise NotImplementedError(
      "Android timer cancellation not implemented; timers are fire-and-forget."
    )
