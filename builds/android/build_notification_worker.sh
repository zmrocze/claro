# shellcheck shell=bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

pushd "$ROOT_DIR/builds/android" >/dev/null

# Buildozer must run inside an FHS env on NixOS (Android SDK tools are dynamically linked).
bash ./run_buildozer_fhs.sh --profile notification android debug

popd >/dev/null
