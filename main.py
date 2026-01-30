"""Android build entrypoint.

This thin wrapper delegates to the existing Android app bootstrap so that
python-for-android/buildozer can locate a `main.py` when packaging.
"""

from entrypoints.claro_app_android import main as run_android_app

if __name__ == "__main__":
  run_android_app()
