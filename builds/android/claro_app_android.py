"""Buildozer module entrypoint.

Buildozer/p4a expects a module import path. We keep this shim under
`builds/android/` and delegate to the real platform entrypoint.
"""

from claro_app_android import main


def run() -> None:
  main()


if __name__ == "__main__":
  run()
