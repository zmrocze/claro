[app]
title = ClaroNotificationScheduler
package.name = claro_scheduler
package.domain = org.claro

source.dir = ../..
source.include_exts = py,json,yaml,toml
source.exclude_dirs = .git,__pycache__,node_modules,dist,build,venv,.devenv,.windsurf,.android,docs,documentations,notes,test,builds,claro.egg-info,python-for-android-moved-from-platform-slash-python-for-android,frontend,~,result,result-2,result2
source.exclude_patterns = setup.py,pyproject.toml,uv.lock,package-lock.json,init_zep.py

# Runs notification_schedule/main.py
package.entrypoint = notification_schedule.main_android

version = 0.1.0

# Scheduler uses platformdirs + yaml parser + timer manager.
# On Android, the timer manager uses pyjnius AlarmManager.
requirements = python3,pyjnius,pyyaml,platformdirs,cython,android

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 29
android.sdk = 34
android.ndk = 25b
android.archs = arm64-v8a,x86_64

android.permissions = POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.12.0

[buildozer]
log_level = 2
warn_on_root = 0
