"""Compatibility shim.

Historically the desktop entrypoint lived in `claro_app.py`.
We now split entrypoints per-platform (Linux/Android) while keeping this import
path stable.
"""

from claro_app_linux import main


if __name__ == "__main__":
  main()
