[app]
title = Claro
package.name = claro
package.domain = org.claro

source.dir = ../..
source.include_exts = py,js,jsx,ts,tsx,html,css,json,yaml,toml
# source.exclude_dirs = .git,__pycache__,node_modules,dist,build,venv,.devenv
source.exclude_patterns = setup.py, pyproject.toml
source.include_patterns = entrypoints/**/*,backend/**/*,os_interfaces/**/*,remember/**/*,notification/**/*,notification_schedule/**/*

# IMPORTANT: buildozer expects a module in the source tree, not a repo-root script.
# We provide a minimal Android entrypoint in builds/android/.
# package.entrypoint = builds.android.claro_app_android

version = 0.1.0

# Original minimal requirements - kept for reference
# requirements = python3,pyjnius,fastapi,uvicorn,pywebview,pyyaml,pydantic,python-dotenv,platformdirs,click,proxy_tools,android,bottle,starlette

# Updated requirements with essential dependencies (versions pinned from uv.lock)
requirements = python3,pyjnius==1.7.0,android,fastapi==0.119.0,uvicorn==0.35.0,pywebview==6.0,pyyaml==6.0.2,pydantic==2.11.9,python-dotenv==1.1.1,platformdirs==4.4.0,click==8.2.1,proxy_tools,android,bottle==0.13.4,starlette==0.47.3,pydantic-core==2.33.2,annotated-types==0.7.0,typing-extensions==4.15.0,typing-inspection==0.4.1,anyio==4.10.0,sniffio==1.3.1,idna==3.10,certifi==2025.8.3,h11==0.16.0,httpcore==1.0.9,httpx==0.28.1,httptools==0.6.4,websockets==15.0.1,charset-normalizer==3.4.3,urllib3==2.5.0,requests==2.32.5,openai==1.107.2,langchain==0.3.27,langchain-core==0.3.76,langchain-openai==0.3.33,langsmith==0.4.27,tiktoken==0.11.0,llama-index-core==0.14.7,jiter==0.10.0,distro==1.9.0,tenacity==9.1.2,jsonpatch==1.33,jsonpointer==3.0.0,orjson==3.11.3,aiohttp==3.13.2,aiosignal==1.4.0,frozenlist==1.8.0,multidict==6.7.0,yarl==1.22.0,attrs==25.4.0,aiohappyeyeballs==2.6.1,six==1.17.0,setuptools==80.9.0,asgi-correlation-id==4.3.4,slowapi==0.1.9,limits==5.6.0,langgraph==0.6.7,langgraph-checkpoint==2.1.1,langgraph-prebuilt==0.6.4,langgraph-sdk==0.2.6,langchain-xai==0.2.5,zep-cloud==3.4.3,python-dateutil==2.9.0.post0,deprecated==1.2.18,packaging==25.0,xxhash==3.5.0,requests-toolbelt==1.0.0,wrapt==1.17.3,regex==2025.9.1,dataclasses-json==0.6.7,marshmallow==3.26.1,langchain-text-splitters==0.3.11,zstandard==0.24.0,propcache==0.4.1,jinja2==3.1.6,markupsafe==3.0.3,typing-inspect==0.9.0,mypy-extensions==1.1.0,sqlalchemy==2.0.43,greenlet==3.2.4,networkx==3.5,nltk==3.9.2,dirtyjson==1.0.8,fsspec==2025.10.0,aiosqlite==0.21.0,tzdata==2025.2,pytz==2025.2,zep-python==2.0.2,joblib==1.5.2,llama-index-instrumentation==0.4.2,llama-index-readers-file==0.5.4,llama-index-workflows==2.10.3,pypdf==6.1.3,striprtf==0.0.26,filetype==1.2.0,mistletoe==1.5.0,appdirs==1.4.4,defusedxml==0.7.1,banks==2.2.0,ormsgpack==1.10.0
p4a.local_recipes = ./p4a_recipes
p4a.setup_py = false

orientation = portrait
fullscreen = 0

android.api = 34
android.minapi = 31
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
