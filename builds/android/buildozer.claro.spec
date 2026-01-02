[app]
title = Claro
package.name = claro
package.domain = org.claro

source.dir = ../..
source.include_exts = py,js,jsx,ts,tsx,html,css,json,yaml,toml
source.exclude_dirs = .git,__pycache__,node_modules,dist,build,venv,.devenv

# IMPORTANT: buildozer expects a module in the source tree, not a repo-root script.
# We provide a minimal Android entrypoint in builds/android/.
package.entrypoint = builds.android.claro_app_android

version = 0.1.0

requirements = python3,pyjnius,fastapi,uvicorn,pywebview,pyyaml,pydantic,python-dotenv,platformdirs
p4a.local_recipes = ./p4a_recipes

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 29
android.sdk = 34
android.ndk = 25b
android.archs = arm64-v8a,x86_64

android.permissions = INTERNET,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED
android.enable_androidx = True

# Needed for NotificationCompat on Android 13+.
android.gradle_dependencies = androidx.core:core:1.12.0

[buildozer]
log_level = 2
warn_on_root = 0
