from setuptools import find_packages, setup

# Minimal setup.py to allow pip installation in environments (like p4a) that
# default to legacy builds and need explicit python_requires plus py_modules
# for top-level entrypoint files.

# core_py_modules = [
#   "claro_app_android",
#   "claro_app_core",
#   "claro_app",
#   "claro_app_linux",
# ]

package_list = find_packages(
  include=[
    "entrypoints",
    "entrypoints.*",
    "backend",
    "backend.*",
    "os_interfaces",
    "os_interfaces.*",
    "remember",
    "remember.*",
    "notification",
    "notification.*",
    "notification_schedule",
    "notification_schedule.*",
  ]
)

setup(
  name="claro",
  version="0.1.0",
  description="Personal AI assistant app with chat interface and notifications",
  python_requires=">=3.11",
  packages=package_list,
  include_package_data=True,
  install_requires=[
    "fastapi==0.119.0",
    "uvicorn[standard]",
    "pywebview",
    "pyyaml",
    "pydantic",
    "python-dotenv",
    "platformdirs",
    "pyjnius",
  ],
  extras_require={
    "android": ["pyjnius", "cython==3.0.12", "buildozer"],
    "linux": ["desktop-notifier", "pystemd"],
    "dev": ["pytest", "pytest-asyncio", "pytest-cov"],
  },
)
