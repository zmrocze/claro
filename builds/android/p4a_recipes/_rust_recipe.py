"""
Shared base class for p4a recipes that build Rust/maturin Python extensions
and need to cross-compile for Android using the NDK clang as the cargo linker.
"""

from os.path import join

from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.logger import info
from pythonforandroid.util import current_directory
import sh


# Maps p4a arch names -> Rust target triples
RUST_TARGETS = {
  "arm64-v8a": "aarch64-linux-android",
  "x86_64": "x86_64-linux-android",
  "armeabi-v7a": "armv7-linux-androideabi",
  "x86": "i686-linux-android",
}

# Maps p4a arch names -> Linux kernel arch names used in Python build dirs
LINUX_ARCH_NAMES = {
  "arm64-v8a": "aarch64",
  "x86_64": "x86_64",
  "armeabi-v7a": "arm",
  "x86": "i686",
}


class RustPythonRecipe(PythonRecipe):
  """Base recipe for Python packages that use maturin/setuptools-rust.

  Subclasses only need to set ``version``, ``url``, and optionally
  ``site_packages_name`` / ``depends`` / ``python_depends``.
  """

  call_hostpython_via_targetpython = False
  install_in_hostpython = False

  def get_recipe_env(self, arch=None, with_flags_in_cc=True):
    env = super().get_recipe_env(arch, with_flags_in_cc)
    if arch is None:
      return env

    rust_triple = RUST_TARGETS.get(arch.arch)
    if rust_triple is None:
      raise ValueError(f"No Rust target triple for arch: {arch.arch}")

    # Use the target-prefixed clang (e.g. x86_64-linux-android29-clang)
    # so it automatically finds the NDK sysroot (crtbeginS.o, liblog, etc.)
    linker = arch.get_clang_exe(with_target=True, plus_plus=False)

    # Cargo target-specific linker env var
    triple_upper = rust_triple.upper().replace("-", "_")
    env[f"CARGO_TARGET_{triple_upper}_LINKER"] = linker

    # Default build target for cargo
    env["CARGO_BUILD_TARGET"] = rust_triple

    # Path to libpython3.X.so for the target Android Python build
    py_build_dir = join(
      self.ctx.build_dir,
      "other_builds",
      "python3",
      f"{arch.arch}__ndk_target_{self.ctx.ndk_api}",
      "python3",
      "android-build",
    )

    # RUSTFLAGS: use NDK linker, allow unresolved shlibs, add python lib path
    env["RUSTFLAGS"] = (
      f"-C linker={linker} "
      "-C link-arg=-Wl,--allow-shlib-undefined "
      f"-L native={py_build_dir}"
    )

    # NDK info for maturin / pyo3-build-config
    env["ANDROID_NDK_HOME"] = self.ctx.ndk_dir
    env["ANDROID_API_LEVEL"] = str(self.ctx.ndk_api)

    # Keep cargo's home inside the build tree (NixOS FHS safety)
    if "CARGO_HOME" not in env:
      env["CARGO_HOME"] = join(self.ctx.build_dir, ".cargo")

    return env

  def build_arch(self, arch):
    env = self.get_recipe_env(arch)
    rust_triple = RUST_TARGETS[arch.arch]
    install_dir = self.ctx.get_python_install_dir(arch.arch)

    # maturin cross-compile: pass target triple and interpreter version string
    # (maturin rejects a path to python when cross-compiling)
    py_ver = self.ctx.python_recipe.version  # e.g. '3.11.5'
    py_ver_short = ".".join(py_ver.split(".")[:2])  # e.g. '3.11'

    # Directory containing the target Android _sysconfigdata*.py + libpython
    linux_arch = LINUX_ARCH_NAMES[arch.arch]
    py_lib_dir = join(
      self.ctx.build_dir,
      "other_builds",
      "python3",
      f"{arch.arch}__ndk_target_{self.ctx.ndk_api}",
      "python3",
      "android-build",
      "build",
      f"lib.linux-{linux_arch}-{py_ver_short}",
    )
    env["MATURIN_PEP517_ARGS"] = f"--target {rust_triple}"
    env["PYO3_CROSS"] = "1"
    env["PYO3_CROSS_LIB_DIR"] = py_lib_dir
    env["PYO3_CROSS_PYTHON_VERSION"] = py_ver_short

    info(f"Building {self.name} for {arch.arch} (Rust target: {rust_triple})")

    with current_directory(self.get_build_dir(arch.arch)):
      # Ensure the Rust Android target is available
      sh.Command("rustup")("target", "add", rust_triple, _env=env)
      # Cross-compile and install via pip.
      # Do NOT use --no-build-isolation: pip needs to install build
      # backends (maturin / setuptools-rust) into an isolated env.
      sh.Command("pip")(
        "install",
        "--no-deps",
        f"--target={install_dir}",
        ".",
        _env=env,
      )
