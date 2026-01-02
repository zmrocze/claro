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

# Ensure Buildozer sees the intended spec file (some tools ignore BUILDOZER_SPECFILE).
ln -sf "$spec_path" "$(pwd)/buildozer.spec"

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
libffi_lib=""
for p in /nix/store/*-libffi-*/lib; do
  if ls "$p"/libffi.so* >/dev/null 2>&1; then
    libffi_lib="$p"
    break
  fi
done
libffi_include=""
for p in /nix/store/*-libffi-*/include; do
  if [ -f "$p/ffi.h" ]; then
    libffi_include="$p"
    break
  fi
done
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

# Ensure libtoolize, GNU m4, autoreconf, and aclocal are available for autoreconf-heavy recipes (e.g., libffi).
libtool_bin=""
libtool_aclocal=""
for p in /nix/store/*-libtool-*/bin/libtoolize; do
  libtool_bin="$(dirname "$p")"
  # libtool installs aclocal macros alongside the binary
  prefix="$(dirname "$libtool_bin")"
  if [ -d "$prefix/share/aclocal" ]; then
    libtool_aclocal="$prefix/share/aclocal"
  fi
  break
done
m4_bin=""
for p in /nix/store/*-gnum4-*/bin/m4; do
  m4_bin="$(dirname "$p")"
  break
done
autoconf_bin=""
for p in /nix/store/*-autoconf-*/bin/autoreconf; do
  autoconf_bin="$(dirname "$p")"
  break
done
automake_bin=""
automake_aclocal=""
for p in /nix/store/*-automake-*/bin/aclocal; do
  automake_bin="$(dirname "$p")"
  prefix="$(dirname "$automake_bin")"
  if [ -d "$prefix/share/aclocal" ]; then
    automake_aclocal="$prefix/share/aclocal"
  fi
  break
done

extra_path="$PATH"
if [ -n "$libtool_bin" ]; then
  extra_path="$libtool_bin:$extra_path"
fi
if [ -n "$m4_bin" ]; then
  extra_path="$m4_bin:$extra_path"
fi
if [ -n "$autoconf_bin" ]; then
  extra_path="$autoconf_bin:$extra_path"
fi
if [ -n "$automake_bin" ]; then
  extra_path="$automake_bin:$extra_path"
fi

# Build an ACLOCAL_PATH that always includes libtool/automake macros even if
# the outer environment forgot to set it (common source of AC_PROG_LIBTOOL
# failures when autoreconf runs for libffi).
aclocal_path_parts=()
if [ -n "$libtool_aclocal" ]; then
  aclocal_path_parts+=("$libtool_aclocal")
fi
if [ -n "$automake_aclocal" ]; then
  aclocal_path_parts+=("$automake_aclocal")
fi
if [ -n "${ACLOCAL_PATH:-}" ]; then
  aclocal_path_parts+=("$ACLOCAL_PATH")
fi
aclocal_path=""
if [ "${#aclocal_path_parts[@]}" -gt 0 ]; then
  IFS=":" aclocal_path="${aclocal_path_parts[*]}"; IFS=" "
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
if [ -n "$extra_path" ]; then
  env_parts+=("PATH=$extra_path")
fi
if [ -n "$aclocal_path" ]; then
  env_parts+=("ACLOCAL_PATH=$aclocal_path")
fi
if [ -n "$libffi_include" ]; then
  env_parts+=("LIBFFI_INCLUDEDIR=$libffi_include")
fi
if [ -n "$libffi_lib" ]; then
  env_parts+=("LIBFFI_LIBDIR=$libffi_lib")
  env_parts+=("LIBFFI_LIBS=-lffi")
fi
ld_parts=()
if [ -n "$libffi_lib" ]; then
  ld_parts+=("$libffi_lib")
fi
if [ -d "$bt_lib64" ]; then
  ld_parts+=("$bt_lib64")
fi
if [ -n "${LD_LIBRARY_PATH:-}" ]; then
  ld_parts+=("$LD_LIBRARY_PATH")
fi
if [ "${#ld_parts[@]}" -gt 0 ]; then
  IFS=":" env_parts+=("LD_LIBRARY_PATH=${ld_parts[*]}"); IFS=" "
fi

# spec_path_escaped=$(printf '%q' "$spec_path")
cmd="env ${env_parts[*]} uv run buildozer -- ${escaped_args[*]}"
exec "$BUILDOZER_FHS" -c "bash -lc $(printf '%q' "$cmd")"
