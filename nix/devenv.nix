{
  perSystem = { pkgs, lib, ...}:
    {
      devenv.shells.default = {
        cachix.enable = true;
        
        # Disable containers to avoid nix2container dependency
        containers = lib.mkForce { };

        # https://devenv.sh/basics/
        env = {
          GREET = "devenv";
          PKG_CONFIG_PATH = lib.makeSearchPath "lib/pkgconfig" [
            pkgs.openssl.dev
            pkgs.libffi.dev
          ];
          ACLOCAL_PATH = lib.makeSearchPath "share/aclocal" [
            pkgs.automake
            pkgs.libtool
          ];
        };
        enterShell = ''
          echo "$GREET"
        '';

        packages = with pkgs; [
          systemd
          pinentry
          python312Packages.cython
          # NOTE: This project uses *Python Buildozer* (PyPI package `buildozer`)
          # for Android builds (via python-for-android), NOT Bazel's buildozer.
          # python312packages.pystemd
        ];

        # FHS wrapper for NixOS so Android SDK tools (e.g. `aidl`) can run.
        # This follows the "Best Solution: systemFHSEnv for Buildozer" approach
        # from `documentations/NixOS + Buildozer AIDL Runtime Issue.md`.
        env.BUILDOZER_FHS = "${pkgs.buildFHSEnv {
          name = "buildozer-fhs";
          runScript = "bash";
          targetPkgs = pkgs: with pkgs; [ 
            cmake
            autoconf
            automake
            libtool
            m4
            pkg-config
            libffi
            libffi.dev

            # Runtime deps for Android SDK binaries (aidl, aapt2, etc.)
            glibc
            zlib
            ncurses5
            libxcrypt
            libuuid

            # C++ runtime bits these tools link against
            libcxx
            libgcc
            stdenv.cc.cc.lib
          ];
        }}/bin/buildozer-fhs";

        # --- Android helper commands (exposed as `devenv run <name>`) ---
        scripts = {
          android-build-app.exec = ''
            set -euo pipefail
            bash ./builds/android/build_claro_app.sh
          '';

          android-build-notification-worker.exec = ''
            set -euo pipefail
            bash ./builds/android/build_notification_worker.sh
          '';

          android-build-notification-scheduler.exec = ''
            set -euo pipefail
            bash ./builds/android/build_notification_scheduler.sh
          '';

          # Low-level helper: run Buildozer inside the FHS environment.
          # Usage: devenv run buildozer-fhs -- <buildozer args>
          buildozer-fhs.exec = ''
            set -euo pipefail
            bash ./builds/android/run_buildozer_fhs.sh "$@"
          '';

          # Best-effort check: can the Buildozer-managed `aidl` run inside FHS?
          # This mirrors Buildozer's own failure mode and helps diagnose quickly.
          android-check-aidl.exec = ''
            set -euo pipefail
            AIDL_PATH="$HOME/.buildozer/android/platform/android-sdk/build-tools/36.1.0/aidl"
            BT_LIB64="$HOME/.buildozer/android/platform/android-sdk/build-tools/36.1.0/lib64"
            if [ ! -e "$AIDL_PATH" ]; then
              echo "aidl not found at: $AIDL_PATH"
              echo "(Run a build once so Buildozer downloads the SDK.)"
              exit 0
            fi
            CMD="'$AIDL_PATH' --help"
            if [ -d "$BT_LIB64" ]; then
              CMD="LD_LIBRARY_PATH=$BT_LIB64:\$LD_LIBRARY_PATH $CMD"
            fi

            "$BUILDOZER_FHS" -c "$CMD" >/dev/null 2>&1 \
              && echo "aidl OK" \
              || (echo "aidl FAILED" && "$BUILDOZER_FHS" -c "$CMD" && exit 1)
          '';

          android-emulator-create.exec = ''
            set -euo pipefail
            NAME="''${1:-claro-emulator}"
            API="''${2:-34}"
            ABI="''${3:-x86_64}"
            DEVICE="''${4:-pixel_5}"

            IMG="system-images;android-''${API};google_apis_playstore;''${ABI}"
            SDK_ROOT="''${ANDROID_SDK_ROOT:-$ANDROID_HOME}"

            # Locate avdmanager (prefer cmdline-tools latest, then 11.0, then PATH)
            if [ -n "$SDK_ROOT" ] && [ -x "$SDK_ROOT/cmdline-tools/latest/bin/avdmanager" ]; then
              AVDMGR="$SDK_ROOT/cmdline-tools/latest/bin/avdmanager"
            elif [ -n "$SDK_ROOT" ] && [ -x "$SDK_ROOT/cmdline-tools/11.0/bin/avdmanager" ]; then
              AVDMGR="$SDK_ROOT/cmdline-tools/11.0/bin/avdmanager"
            else
              AVDMGR="$(command -v avdmanager || true)"
            fi

            if [ -z "$AVDMGR" ]; then
              echo "avdmanager not found in PATH or SDK (ANDROID_SDK_ROOT/ANDROID_HOME)" >&2
              exit 1
            fi

            DEVICE_FLAG="--device $DEVICE"
            if ! "$AVDMGR" list device | grep -Fq "\"$DEVICE\""; then
              echo "Device '$DEVICE' not found; using 'pixel' if available" >&2
              if "$AVDMGR" list device | grep -Fq "\"pixel\""; then
                DEVICE_FLAG="--device pixel"
              else
                DEVICE_FLAG=""
              fi
            fi

            "$AVDMGR" create avd --force --name "$NAME" --package "$IMG" --abi "$ABI" $DEVICE_FLAG
          '';

          android-emulator-start.exec = ''
            set -euo pipefail
            NAME="''${1:-claro-emulator}"
            emulator -avd "$NAME" -netdelay none -netspeed full &
            adb wait-for-device
            adb shell getprop sys.boot_completed
          '';

          android-install-app.exec = ''
            set -euo pipefail
            APK_GLOB="''${1:-./builds/android/bin/claro-*-debug.apk}"
            # shellcheck disable=SC2086
            adb install -r $APK_GLOB
          '';

          android-launch-app.exec = ''
            set -euo pipefail
            PKG="''${1:-org.claro}"
            adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1
          '';

          android-logcat-python.exec = ''
            set -euo pipefail
            adb logcat -s python:V
          '';

          android-logcat-app.exec = ''
            set -euo pipefail
            adb logcat -s claro:V python:V
          '';

          android-grant-notifications.exec = ''
            set -euo pipefail
            PKG="''${1:-org.claro}"
            adb shell pm grant "$PKG" android.permission.POST_NOTIFICATIONS || true
          '';

          android-check-network.exec = ''
            set -euo pipefail
            adb shell "ping -c1 8.8.8.8"
          '';

          android-check-storage.exec = ''
            set -euo pipefail
            PKG="''${1:-org.claro}"
            adb shell ls "/sdcard/Android/data/$PKG/files/" || true
          '';

          local-jupyter.exec = "uv run jupyter notebook --no-browser --ip=127.0.0.1 --port=8888 --NotebookApp.token= --NotebookApp.password= --NotebookApp.allow_origin=*";

          generate-types.exec = ''
            echo "🔄 Generating TypeScript types from FastAPI backend..."
            
            # Check if backend is already running
            BACKEND_RUNNING=false
            if curl -s http://localhost:8000/health > /dev/null 2>&1; then
              echo "✓ Backend is already running"
              BACKEND_RUNNING=true
            else
              echo "⚙️  Starting backend temporarily..."
              uv run -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 > /dev/null 2>&1 &
              BACKEND_PID=$!
              
              # Wait for backend to be ready (max 30 seconds)
              echo "⏳ Waiting for backend to start..."
              for i in {1..30}; do
                if curl -s http://localhost:8000/health > /dev/null 2>&1; then
                  echo "✓ Backend is ready"
                  break
                fi
                sleep 1
              done
            fi
            
            # Generate types
            echo "📝 Generating TypeScript types..."
            cd frontend
            npm run generate-types
            cd ..
            
            # Stop backend if we started it
            if [ "$BACKEND_RUNNING" = false ]; then
              echo "🛑 Stopping temporary backend..."
              kill $BACKEND_PID 2>/dev/null || true
            fi
            
            echo "✅ TypeScript types generated successfully in frontend/src/api-client/"
          '';
        };

        # https://devenv.sh/tests/
        enterTest = ''
          echo "Running tests"
        '';

        languages = {
          python = {
            enable = true;
            uv = {
              enable = true;
              sync = {
                enable = true;
                allExtras = true;
                allGroups = true;
              };
            };
            package = pkgs.python312;
            # version = "3.12";
          };
          javascript = {
            enable = true;
            package = pkgs.nodejs_20;
            npm = {
              enable = true;
              install.enable = true;
            };
          };
          typescript = {
            enable = true;
          };

          nix = {
            enable = true;
          };
        };

        # https://devenv.sh/git-hooks/
        git-hooks.hooks = {
          shellcheck.enable = true;
          # markdownlint.enable = true; # waste of time
          
          deadnix.enable = true;
          statix.enable = true;
          # nixfmt.enable = true;
          nil.enable = true;

          uv-check.enable = true;
          ruff.enable = true;
          ruff-format.enable = true;
          pyright.enable = true;

          denolint = {
            enable = true;
            excludes = [ "src/api-client/" ];  # Directories to exclude
          };
          denofmt = {
            enable = true;
            excludes = [ "src/api-client/" ];  # Directories to exclude
          };
          # eslint.enable = true;

          # html-tidy.enable = true;
        };

        android = {
          enable = true;
          # enable = false;
          # 34 = Android 14, 33 = Android 13. 
          # Keeping 34 is recommended for new apps.
          platforms.version = [ "34" "35" ]; 
          systemImageTypes = [ "google_apis_playstore" ];
          abis = [ "arm64-v8a" "x86_64" ];
          cmake.version = [ "3.22.1" ];
          # 11.0 is the current latest stable version of cmdline-tools
          cmdLineTools.version = "11.0"; 
          buildTools.version = [ "35.0.0" ]; 
          emulator = {
            enable = true;
          };
          sources.enable = false;
          systemImages.enable = true;
          googleAPIs.enable = true;
          googleTVAddOns.enable = true;
          extras = [ "extras;google;gcm" ];
          extraLicenses = [
            "android-sdk-preview-license"
            "android-googletv-license"
            "android-sdk-arm-dbt-license"
            "google-gdk-license"
            "intel-android-extra-license"
            "intel-android-sysimage-license"
            "mips-android-sysimage-license"
          ];
          android-studio = {
            enable = true;
            package = pkgs.android-studio;
          };
          # NDK: Python-for-Android is sensitive to NDK versions.
          # r25b (25.2.9519653) is the current robust standard for p4a.
          ndk = {
            enable = true;
            version = ["25.2.9519653"];
          };
        };

        # Language support (Java 17 is standard for Android 13+)
        languages.java.enable = true;
        languages.java.jdk.package = pkgs.jdk17;
        # # 4. ENVIRONMENT VARIABLES
        # # We export these so Buildozer knows where to look for the tools.
        # # Note: config.android.sdk.path is the Nix store path to the composed SDK.
        # env.JAVA_HOME = config.languages.java.jdk.home;
        # env.ANDROID_HOME = config.android.sdk.path;
        # env.NDK_HOME = "${config.android.sdk.path}/ndk/25.2.9519653";

        # See full reference at https://devenv.sh/reference/options/
      };
    };
}
