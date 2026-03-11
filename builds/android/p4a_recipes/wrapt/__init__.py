from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class WraptRecipe(CompiledComponentsPythonRecipe):
  version = "1.17.3"
  url = "https://files.pythonhosted.org/packages/source/w/wrapt/wrapt-{version}.tar.gz"
  site_packages_name = "wrapt"
  call_hostpython_via_targetpython = False
  depends = ["setuptools"]


recipe = WraptRecipe()
