"""
Shared base class for p4a recipes that build C-extension Python packages
using PEP 517 build systems (pyproject.toml) and need to cross-compile
for Android using the NDK.

These packages do NOT have a setup.py, so the standard
CompiledComponentsPythonRecipe (which calls `setup.py build_ext`) fails.
Instead, we use `pip install --no-deps --no-build-isolation --target=... .`
with the NDK cross-compilation environment already set by p4a's arch.get_env().

Cross-compilation is driven entirely by env vars (CC, CXX, CFLAGS, LDFLAGS,
LDSHARED) — we do NOT set _PYTHON_SYSCONFIGDATA_NAME because that poisons
pip's host Python sysconfig and breaks isolated builds.

This is analogous to _rust_recipe.py but for pure C/Cython extensions.
"""

from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.logger import info
from pythonforandroid.util import current_directory
import sh


class CExtPythonRecipe(PythonRecipe):
  """Base recipe for Python C-extension packages that use PEP 517 builds
  (pyproject.toml with setuptools/Cython backend) and have no setup.py.

  Uses ``pip install --no-deps --no-build-isolation --target=...`` with
  the NDK CC/CXX/CFLAGS/LDFLAGS/LDSHARED already configured by p4a.

  Subclasses only need to set ``version``, ``url``, and optionally
  ``site_packages_name`` / ``depends`` / ``python_depends``.
  """

  call_hostpython_via_targetpython = False
  install_in_hostpython = False

  def get_recipe_env(self, arch=None, with_flags_in_cc=True):
    env = super().get_recipe_env(arch, with_flags_in_cc)
    if arch is None:
      return env

    # Ensure LDSHARED is set for shared library linking
    env["LDSHARED"] = env["CC"] + " -shared"

    # Add extra link paths (bootstrap libs, etc.)
    env["LDFLAGS"] = env["LDFLAGS"] + " -L{}".format(self.ctx.get_libs_dir(arch.arch))

    # Python include path for the target
    env["CFLAGS"] += " -I{}".format(self.ctx.python_recipe.include_root(arch.arch))
    env["LDFLAGS"] += " -L{} -lpython{}".format(
      self.ctx.python_recipe.link_root(arch.arch),
      self.ctx.python_recipe.link_version,
    )

    return env

  def build_arch(self, arch):
    env = self.get_recipe_env(arch)
    install_dir = self.ctx.get_python_install_dir(arch.arch)

    info(
      f"Building {self.name} for {arch.arch} via pip install "
      f"(PEP 517 C-extension cross-compile)"
    )

    with current_directory(self.get_build_dir(arch.arch)):
      # Use pip to build & install.  --no-build-isolation so that
      # pip does NOT create a temp venv (which would ignore our
      # env vars for CC/LDSHARED).  The host buildozer venv already
      # has setuptools + Cython installed, so build deps are met.
      sh.Command("pip")(
        "install",
        "--no-deps",
        "--no-build-isolation",
        f"--target={install_dir}",
        ".",
        _env=env,
      )
