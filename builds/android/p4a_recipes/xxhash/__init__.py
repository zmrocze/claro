from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class XXHashRecipe(CompiledComponentsPythonRecipe):
  version = "3.5.0"
  url = (
    "https://files.pythonhosted.org/packages/source/x/xxhash/xxhash-{version}.tar.gz"
  )
  site_packages_name = "xxhash"
  call_hostpython_via_targetpython = False
  depends = ["setuptools"]


recipe = XXHashRecipe()
