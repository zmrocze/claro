import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _rust_recipe import RustPythonRecipe


class JiterRecipe(RustPythonRecipe):
  version = "0.10.0"
  url = "https://files.pythonhosted.org/packages/source/j/jiter/jiter-{version}.tar.gz"
  depends = ["setuptools", "hostpython3"]
  site_packages_name = "jiter"


recipe = JiterRecipe()
