"""Android entrypoint for the packaged Claro app.

Buildozer/p4a expects a Python *module* entrypoint. Our desktop entrypoint
`claro_app.py` is a repo-root script, so we keep this tiny shim.

For now, this simply runs the same app bootstrap.
"""

from claro_app import main


def run():
  main()


if __name__ == "__main__":
  run()
