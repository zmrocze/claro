from pythonforandroid.recipe import PythonRecipe


class SQLAlchemyRecipe(PythonRecipe):
  """SQLAlchemy's C extensions require Cython and are optional speedups.
  Install as pure-Python via setup.py install (no build_ext)."""

  name = "sqlalchemy"
  version = "2.0.43"
  url = "https://files.pythonhosted.org/packages/source/s/sqlalchemy/sqlalchemy-{version}.tar.gz"
  site_packages_name = "sqlalchemy"
  call_hostpython_via_targetpython = False
  depends = ["setuptools", "greenlet"]


recipe = SQLAlchemyRecipe()
