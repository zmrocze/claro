import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _rust_recipe import RustPythonRecipe


class TiktokenRecipe(RustPythonRecipe):
  version = "0.11.0"
  url = "https://files.pythonhosted.org/packages/source/t/tiktoken/tiktoken-{version}.tar.gz"
  depends = ["setuptools", "hostpython3"]
  site_packages_name = "tiktoken"


recipe = TiktokenRecipe()
