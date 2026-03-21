[app]
title = ClaroNotificationWorker
package.name = claro_notifier
package.domain = org.claro
source.dir = ../..
source.include_exts = py,json,yaml,toml
source.exclude_dirs = .git,__pycache__,node_modules,dist,build,venv,.devenv,.windsurf,.android,docs,documentations,notes,test,builds,claro.egg-info,python-for-android-moved-from-platform-slash-python-for-android,frontend,~,result,result-2,result2
source.exclude_patterns = setup.py,pyproject.toml,uv.lock,package-lock.json,init_zep.py

package.entrypoint = notification.main_android

version = 0.1.0
requirements = python3,pyjnius,pyyaml,platformdirs,android
orientation = portrait
fullscreen = 0
android.api = 34
android.minapi = 29
android.sdk = 34
android.ndk = 25b
android.archs = arm64-v8a,x86_64
android.permissions = POST_NOTIFICATIONS
android.enable_androidx = True

android.gradle_dependencies = androidx.core:core:1.12.0,androidx.security:security-crypto:1.0.0

[buildozer]
log_level = 2
warn_on_root = 0
