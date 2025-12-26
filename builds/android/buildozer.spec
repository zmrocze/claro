[app]
title = ClaroNotificationScheduler
package.name = claro_scheduler
package.domain = org.claro

source.dir = ../..
source.include_exts = py,json,yaml,toml
source.exclude_dirs = .git,__pycache__,node_modules,dist,build,venv,.devenv

# Runs notification_schedule/main.py
package.entrypoint = notification_schedule.main_android

version = 0.1.0

# Scheduler uses platformdirs + yaml parser + timer manager.
# On Android, the timer manager uses pyjnius AlarmManager.
requirements = python3,pyjnius,pyyaml,platformdirs,cython

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 29
# android.sdk = 33
android.ndk = 25b
android.archs = arm64-v8a,x86_64

android.permissions = POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.12.0

[buildozer]
log_level = 2
warn_on_root = 0
