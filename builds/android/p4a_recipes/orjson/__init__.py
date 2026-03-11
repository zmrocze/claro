import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _rust_recipe import RustPythonRecipe


class OrjsonRecipe(RustPythonRecipe):
  version = "3.11.3"
  url = (
    "https://files.pythonhosted.org/packages/source/o/orjson/orjson-{version}.tar.gz"
  )
  depends = ["setuptools", "hostpython3"]
  site_packages_name = "orjson"


recipe = OrjsonRecipe()
