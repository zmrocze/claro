# shellcheck shell=bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

pushd "$ROOT_DIR/builds/android" >/dev/null

# Clear any stale distribution built with an older compileSdk.
rm -rf .buildozer/android/platform/build-arm64-v8a_x86_64/dists/claro_scheduler

# Buildozer must run inside an FHS env on NixOS (Android SDK tools are dynamically linked).
bash ./run_buildozer_fhs.sh --profile scheduler android debug4

popd >/dev/null
