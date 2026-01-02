import os
from multiprocessing import cpu_count
from pathlib import Path
from os.path import join

import sh

from pythonforandroid.logger import shprint
from pythonforandroid.prerequisites import OpenSSLPrerequisite
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import (
    BuildInterruptingException,
    current_directory,
    ensure_dir,
)


HOSTPYTHON_VERSION_UNSET_MESSAGE = "The hostpython recipe must have set version"

SETUP_DIST_NOT_FIND_MESSAGE = "Could not find Setup.dist or Setup in Python build"


class HostPython3Recipe(Recipe):
    """Local override to force linking hostpython against system libffi.

    The upstream recipe builds fine on most hosts but on Nix the generated
    ``_ctypes`` extension may miss ``-lffi`` during hostpython's build. We
    inject libffi include/lib flags and explicitly pass ``--with-system-ffi``
    to configure so ``_ctypes`` links correctly.
    """

    version = "3.11.5"
    name = "hostpython3"

    build_subdir = "native-build"

    url = "https://www.python.org/ftp/python/{version}/Python-{version}.tgz"

    patches = ["patches/pyconfig_detection.patch"]

    @property
    def _exe_name(self):
        if not self.version:
            raise BuildInterruptingException(HOSTPYTHON_VERSION_UNSET_MESSAGE)
        return f"python{self.version.split('.')[0]}"

    @property
    def python_exe(self):
        return join(self.get_path_to_python(), self._exe_name)

    def get_recipe_env(self, arch=None):
        env = os.environ.copy()

        # Ensure OpenSSL pkg-config is preferred as upstream does.
        openssl_prereq = OpenSSLPrerequisite()
        if env.get("PKG_CONFIG_PATH", ""):
            env["PKG_CONFIG_PATH"] = os.pathsep.join(
                [openssl_prereq.pkg_config_location, env["PKG_CONFIG_PATH"]]
            )
        else:
            env["PKG_CONFIG_PATH"] = openssl_prereq.pkg_config_location

        # Force libffi flags so _ctypes links properly on host build.
        libffi_include = env.get("LIBFFI_INCLUDEDIR")
        libffi_libdir = env.get("LIBFFI_LIBDIR")
        libffi_libs = env.get("LIBFFI_LIBS", "-lffi")

        cppflags = []
        ldflags = []
        libs = []

        if libffi_include:
            cppflags.append(f"-I{libffi_include}")
        if libffi_libdir:
            ldflags.append(f"-L{libffi_libdir}")
        if libffi_libs:
            libs.append(libffi_libs)

        if cppflags:
            env["CPPFLAGS"] = " ".join(cppflags + [env.get("CPPFLAGS", "")]).strip()
        if ldflags:
            env["LDFLAGS"] = " ".join(ldflags + [env.get("LDFLAGS", "")]).strip()
        if libs:
            env["LIBS"] = " ".join(libs + [env.get("LIBS", "")]).strip()

        return env

    def should_build(self, arch):
        if Path(self.python_exe).exists():
            self.ctx.hostpython = self.python_exe
            return False
        return True

    def get_build_container_dir(self, arch=None):
        choices = self.check_recipe_choices()
        dir_name = "-".join([self.name] + choices)
        return join(self.ctx.build_dir, "other_builds", dir_name, "desktop")

    def get_build_dir(self, arch=None):
        return join(self.get_build_container_dir(), self.name)

    def get_path_to_python(self):
        return join(self.get_build_dir(), self.build_subdir)

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)

        recipe_build_dir = self.get_build_dir(arch.arch)
        build_dir = join(recipe_build_dir, self.build_subdir)
        ensure_dir(build_dir)

        with current_directory(build_dir):
            if not Path("config.status").exists():
                shprint(
                    sh.Command(join(recipe_build_dir, "configure")),
                    "--with-system-ffi",
                    _env=env,
                )

        with current_directory(recipe_build_dir):
            setup_dist_location = join("Modules", "Setup.dist")
            if Path(setup_dist_location).exists():
                shprint(sh.cp, setup_dist_location, join(build_dir, "Modules", "Setup"))
            else:
                setup_location = join("Modules", "Setup")
                if not Path(setup_location).exists():
                    raise BuildInterruptingException(SETUP_DIST_NOT_FIND_MESSAGE)

            shprint(sh.make, "-j", str(cpu_count()), "-C", build_dir, _env=env)

            for exe_name in ["python.exe", "python"]:
                exe = join(self.get_path_to_python(), exe_name)
                if Path(exe).is_file():
                    shprint(sh.cp, exe, self.python_exe)
                    break

        self.ctx.hostpython = self.python_exe


recipe = HostPython3Recipe()
