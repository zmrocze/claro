from os.path import join, exists
from multiprocessing import cpu_count
from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
import sh


class LibffiRecipe(Recipe):
    """
    Local override of the upstream libffi recipe that avoids autoreconf
    issues on Nix by using the official release tarball (which already
    contains a generated configure script) and only running autoreconf
    when configure is missing.
    """

    name = "libffi"
    version = "3.4.2"
    url = "https://github.com/libffi/libffi/releases/download/v{version}/libffi-{version}.tar.gz"

    patches = ["remove-version-info.patch"]

    built_libraries = {"libffi.so": ".libs"}

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            # Use the release tarball's pre-generated configure script and
            # skip autoreconf entirely (avoids AC_PROG_LIBTOOL macro issues
            # on Nix). If configure is ever missing, fail fast instead of
            # attempting to regenerate.
            if not exists("configure"):
                raise RuntimeError("libffi configure script missing in release tarball")

            shprint(
                sh.Command("./configure"),
                "--host=" + arch.command_prefix,
                "--prefix=" + self.get_build_dir(arch.arch),
                "--disable-builddir",
                "--enable-shared",
                _env=env,
            )
            shprint(sh.Command("make"), "-j", str(cpu_count()), "libffi.la", _env=env)

    def get_include_dirs(self, arch):
        return [join(self.get_build_dir(arch.arch), "include")]


recipe = LibffiRecipe()
