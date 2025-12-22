"""Android-specific implementations of OS interfaces."""

from __future__ import annotations

import json
import logging
import random
import subprocess
import threading
from datetime import datetime, time
from typing import Callable, Optional

from jnius import PythonJavaClass, autoclass, java_method  # type: ignore

from .base import NotificationManager, ScheduleTimeRange, TimerConfig, TimerManager

logger = logging.getLogger(__name__)


# --- PyJNIus handles ---
PythonActivity = autoclass("org.kivy.android.PythonActivity")
Intent = autoclass("android.content.Intent")
IntentFilter = autoclass("android.content.IntentFilter")
PendingIntent = autoclass("android.app.PendingIntent")
NotificationManagerJava = autoclass("android.app.NotificationManager")
NotificationChannel = autoclass("android.app.NotificationChannel")
BuildVersion = autoclass("android.os.Build$VERSION")
NotificationCompatBuilder = autoclass("androidx.core.app.NotificationCompat$Builder")
NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
AlarmManagerJava = autoclass("android.app.AlarmManager")
Calendar = autoclass("java.util.Calendar")
AndroidRDrawable = autoclass("android.R$drawable")
Context = autoclass("android.content.Context")

ACTION_CLICK = "com.claro.NOTIFICATION_CLICKED"
ACTION_DISMISS = "com.claro.NOTIFICATION_DISMISSED"
ACTION_ALARM_FIRE = "com.claro.ALARM_FIRED"
CHANNEL_ID = "claro-general"


def _context():
  return PythonActivity.mActivity.getApplicationContext()


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


class _AlarmReceiver(PythonJavaClass):
  __javainterfaces__ = ["android/content/BroadcastReceiver"]
  __javacontext__ = "app"

  @java_method("(Landroid/content/Context;Landroid/content/Intent;)V")
  def onReceive(self, _context, intent):
    cmd = intent.getStringExtra("command")
    args_json = intent.getStringExtra("args")
    args = json.loads(args_json) if args_json else []

    def run():
      try:
        subprocess.Popen([cmd, *args])
      except Exception:
        logger.exception("Failed to run alarm command")

    threading.Thread(target=run, daemon=True).start()


_alarm_receiver: _AlarmReceiver | None = None


def _ensure_alarm_receiver(ctx) -> _AlarmReceiver:
  global _alarm_receiver
  if _alarm_receiver is None:
    _alarm_receiver = _AlarmReceiver()
    intent_filter = IntentFilter()
    intent_filter.addAction(ACTION_ALARM_FIRE)
    ctx.registerReceiver(_alarm_receiver, intent_filter)
  return _alarm_receiver


def _rand_request_code() -> int:
  return random.randint(10_000, 99_999)


def _millis(dt: datetime) -> int:
  return int(dt.timestamp() * 1000)


def _pick_datetime(timing: datetime | ScheduleTimeRange) -> datetime:
  if isinstance(timing, ScheduleTimeRange):
    span = timing.to_time - timing.from_time
    return timing.from_time + span * random.random()
  return timing


class AndroidNotificationManager(NotificationManager):
  """Android notification manager using PyJNIus NotificationCompat."""

  def __init__(self):
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
  """Android timer manager using AlarmManager setExact/setRepeating."""

  def __init__(self):
    self.ctx = _context()
    self.alarm_manager = self.ctx.getSystemService(Context.ALARM_SERVICE)
    _ensure_alarm_receiver(self.ctx)

  def schedule_timer(self, timer_config: TimerConfig) -> str:
    target = _pick_datetime(timer_config.timing)
    trigger_at = max(_millis(target), _millis(datetime.now()) + 1000)

    intent = Intent(self.ctx, PythonActivity)
    intent.setAction(ACTION_ALARM_FIRE)
    intent.putExtra("command", timer_config.command)
    intent.putExtra("args", json.dumps(timer_config.args))

    request_code = _rand_request_code()
    pending_intent = PendingIntent.getBroadcast(
      self.ctx, request_code, intent, _flags()
    )

    if BuildVersion.SDK_INT >= 23:
      self.alarm_manager.setExactAndAllowWhileIdle(
        AlarmManagerJava.RTC_WAKEUP, trigger_at, pending_intent
      )
    else:
      self.alarm_manager.setExact(
        AlarmManagerJava.RTC_WAKEUP, trigger_at, pending_intent
      )

    timer_id = f"alarm-{request_code}"
    logger.info("Scheduled alarm %s at %s", timer_id, target.isoformat())
    return timer_id

  def schedule_daily(self, command: str, args: list[str], run_time: time) -> None:
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

    intent = Intent(self.ctx, PythonActivity)
    intent.setAction(ACTION_ALARM_FIRE)
    intent.putExtra("command", command)
    intent.putExtra("args", json.dumps(args))

    pending_intent = PendingIntent.getBroadcast(self.ctx, 42_000, intent, _flags())

    self.alarm_manager.setRepeating(
      AlarmManagerJava.RTC_WAKEUP,
      first_fire,
      AlarmManagerJava.INTERVAL_DAY,
      pending_intent,
    )
    logger.info("Scheduled daily alarm for %s", run_time.isoformat())

  def cancel_timer(self, timer_id: str) -> None:
    # Timer cancellation intentionally omitted (fire-and-forget pattern).
    raise NotImplementedError(
      "Android timer cancellation not implemented; timers are fire-and-forget."
    )
