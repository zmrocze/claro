from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class GreenletRecipe(CompiledComponentsPythonRecipe):
  version = "3.2.4"
  url = "https://files.pythonhosted.org/packages/source/g/greenlet/greenlet-{version}.tar.gz"
  site_packages_name = "greenlet"
  call_hostpython_via_targetpython = False
  depends = ["setuptools"]


recipe = GreenletRecipe()
