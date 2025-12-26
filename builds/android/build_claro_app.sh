# shellcheck shell=bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# Build the web UI so the backend can serve it inside pywebview.
pushd "$ROOT_DIR/frontend" >/dev/null
npm install
npm run build
popd >/dev/null

export CARLO_FRONTEND_PATH="$ROOT_DIR/frontend/dist"

pushd "$ROOT_DIR/builds/android" >/dev/null

# Buildozer must run inside an FHS env on NixOS (Android SDK tools are dynamically linked).
bash ./run_buildozer_fhs.sh --profile claro android debug

popd >/dev/null
