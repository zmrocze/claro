from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class ZstandardRecipe(CompiledComponentsPythonRecipe):
  version = "0.24.0"
  url = "https://files.pythonhosted.org/packages/source/z/zstandard/zstandard-{version}.tar.gz"
  site_packages_name = "zstandard"
  call_hostpython_via_targetpython = False
  depends = ["setuptools"]

  def get_recipe_env(self, arch=None, with_flags_in_cc=True):
    env = super().get_recipe_env(arch, with_flags_in_cc)
    # Force zstd to use the standard C90 qsort instead of qsort_r
    # qsort_r is not available on older Android API levels
    env["CFLAGS"] += " -DZDICT_QSORT=ZDICT_QSORT_C90"
    return env


recipe = ZstandardRecipe()
