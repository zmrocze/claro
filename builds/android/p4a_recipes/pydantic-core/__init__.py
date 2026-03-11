import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from _rust_recipe import RustPythonRecipe


class PydanticCoreRecipe(RustPythonRecipe):
  version = "2.33.2"
  url = "https://files.pythonhosted.org/packages/source/p/pydantic_core/pydantic_core-{version}.tar.gz"
  depends = ["setuptools", "hostpython3"]
  python_depends = ["typing-extensions"]
  site_packages_name = "pydantic_core"


recipe = PydanticCoreRecipe()
