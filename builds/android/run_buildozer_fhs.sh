# shellcheck shell=bash
# NOTE: no shebang (repo rule)
# Run Buildozer inside an FHS environment on NixOS.
#
# Motivation: Android SDK tools (notably `aidl`) are dynamically linked against
# glibc and expect the standard loader path `/lib64/ld-linux-x86-64.so.2`.
# On NixOS that path doesn't exist, so we wrap the build inside an FHS env.
#
# This script expects to be called from within `devenv` so that:
# - `uv` is available and points at the repo's Python environment
# - `BUILDOZER_FHS` is set by `nix/devenv.nix` to the FHS wrapper executable

set -euo pipefail

if [[ -z "${BUILDOZER_FHS:-}" ]]; then
  echo "error: BUILDOZER_FHS is not set. Enter the devenv shell or wire the FHS wrapper." >&2
  echo "hint: the wrapper is defined in nix/devenv.nix (buildFHSEnv)." >&2
  exit 2
fi

# Run buildozer inside the FHS env. We pass args through `bash -lc` and use
# `printf %q` to preserve argument boundaries.
escaped_args=()
for a in "$@"; do
  escaped_args+=("$(printf '%q' "$a")")
done

# Resolve the profile so we can point Buildozer at the correct spec file and
# derive the intended Android API level.
profile=""
parse_args=("$@")
for ((i=0; i<${#parse_args[@]}; i++)); do
  case "${parse_args[$i]}" in
    --profile)
      if (( i + 1 < ${#parse_args[@]} )); then
        profile="${parse_args[$((i+1))]}"
      fi
      ;;
  esac
done

spec_path="$(pwd)/buildozer.spec"
if [[ -n "$profile" ]]; then
  spec_path="$(pwd)/buildozer.${profile}.spec"
fi
if [[ ! -f "$spec_path" ]]; then
  echo "error: buildozer spec not found at $spec_path" >&2
  exit 2
fi

# Read the target API from the spec (android.sdk preferred, then android.api).
target_api=""
spec_sdk=$(awk -F'=' '/^android\.sdk/ {gsub(/ /, "", $2); print $2; exit}' "$spec_path") || true
spec_api=$(awk -F'=' '/^android\.api/ {gsub(/ /, "", $2); print $2; exit}' "$spec_path") || true
if [[ -n "$spec_sdk" ]]; then
  target_api="$spec_sdk"
elif [[ -n "$spec_api" ]]; then
  target_api="$spec_api"
fi
if [[ -z "$target_api" ]]; then
  target_api="34"
fi

bt_lib64="$HOME/.buildozer/android/platform/android-sdk/build-tools/36.1.0/lib64"
sdk_home="$HOME/.buildozer/android/platform/android-sdk"
ndk_home="$HOME/.buildozer/android/platform/android-ndk-r25b"

# Ensure zlib is discoverable for hostpython3 (needed by ensurepip).
pkg_config_path="${PKG_CONFIG_PATH:-}"
zlib_pc=""
for p in /nix/store/*-zlib-*-dev/lib/pkgconfig; do
  zlib_pc="$p"
  break
done
if [ -z "$zlib_pc" ] && command -v nix >/dev/null 2>&1; then
  zlib_dev=$(nix eval --raw nixpkgs#zlib.dev 2>/dev/null || true)
  if [ -n "$zlib_dev" ] && [ -d "$zlib_dev/lib/pkgconfig" ]; then
    zlib_pc="$zlib_dev/lib/pkgconfig"
  fi
fi
if [ -n "$zlib_pc" ]; then
  if [ -n "$pkg_config_path" ]; then
    pkg_config_path="$zlib_pc:$pkg_config_path"
  else
    pkg_config_path="$zlib_pc"
  fi
fi

env_parts=(
  "ANDROIDAPI=$target_api"
  "ANDROID_API=$target_api"
  "ANDROIDSDK=$sdk_home"
  "ANDROID_HOME=$sdk_home"
  "ANDROID_NDK_HOME=$ndk_home"
  "ANDROIDNDK=$ndk_home"
  "ANDROID_NDK_ROOT=$ndk_home"
  "BUILDOZER_SPECFILE=$spec_path"
)
if [ -n "${ACLOCAL_PATH:-}" ]; then
  env_parts+=("ACLOCAL_PATH=${ACLOCAL_PATH}")
fi
if [ -n "$pkg_config_path" ]; then
  env_parts+=("PKG_CONFIG_PATH=$pkg_config_path")
fi
if [ -d "$bt_lib64" ]; then
  env_parts+=("LD_LIBRARY_PATH=$bt_lib64:$LD_LIBRARY_PATH")
fi

cmd="env ${env_parts[*]} uv run buildozer -- ${escaped_args[*]}"
exec "$BUILDOZER_FHS" -c "bash -lc $(printf '%q' "$cmd")"
