from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class RegexRecipe(CompiledComponentsPythonRecipe):
  version = "2025.9.1"
  url = "https://files.pythonhosted.org/packages/source/r/regex/regex-{version}.tar.gz"
  site_packages_name = "regex"
  call_hostpython_via_targetpython = False
  depends = ["setuptools"]


recipe = RegexRecipe()
