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

# Keep this list minimal-ish: p4a will try to build many wheels from source.
# Add more as we confirm Android compatibility.
requirements = python3,pyjnius,fastapi,uvicorn,pywebview,pyyaml,pydantic,python-dotenv,platformdirs

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 29
android.sdk = 33
android.ndk = 25b
android.archs = arm64-v8a,x86_64

android.permissions = INTERNET,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED
android.enable_androidx = True

# Needed for NotificationCompat on Android 13+.
android.gradle_dependencies = androidx.core:core:1.12.0

[buildozer]
log_level = 2
warn_on_root = 0
