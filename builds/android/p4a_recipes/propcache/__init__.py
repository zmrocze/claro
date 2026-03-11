import shutil
from os.path import join, exists

from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.logger import info


class PropcacheRecipe(PythonRecipe):
  """propcache has no setup.py (PEP 517 only with Cython backend).
  The C extension is just a speedup -- the pure-Python fallback works fine.
  We skip compilation and copy the Python source directly."""

  version = "0.4.1"
  url = "https://files.pythonhosted.org/packages/source/p/propcache/propcache-{version}.tar.gz"
  site_packages_name = "propcache"
  call_hostpython_via_targetpython = False

  def build_arch(self, arch):
    src = join(self.get_build_dir(arch.arch), "src", "propcache")
    dest = join(self.ctx.get_python_install_dir(arch.arch), "propcache")
    if exists(dest):
      shutil.rmtree(dest)
    info(f"Copying propcache pure-Python source to {dest}")
    shutil.copytree(src, dest)


recipe = PropcacheRecipe()
