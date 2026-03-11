from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class MarkupSafeRecipe(CompiledComponentsPythonRecipe):
  version = "3.0.3"
  url = "https://files.pythonhosted.org/packages/source/m/markupsafe/markupsafe-{version}.tar.gz"
  site_packages_name = "markupsafe"
  call_hostpython_via_targetpython = False
  depends = ["setuptools"]


recipe = MarkupSafeRecipe()
