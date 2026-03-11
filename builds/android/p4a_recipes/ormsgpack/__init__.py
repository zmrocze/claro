import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _rust_recipe import RustPythonRecipe


class OrmsgpackRecipe(RustPythonRecipe):
  version = "1.10.0"
  url = "https://files.pythonhosted.org/packages/source/o/ormsgpack/ormsgpack-{version}.tar.gz"
  site_packages_name = "ormsgpack"
  depends = ["python3", "setuptools"]


recipe = OrmsgpackRecipe()
