#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

pushd "$ROOT_DIR/builds/android" >/dev/null
buildozer -f buildozer.scheduler.spec android debug
popd >/dev/null
