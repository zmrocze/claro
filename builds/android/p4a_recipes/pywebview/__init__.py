from pythonforandroid.recipe import PythonRecipe
from pythonforandroid.logger import info
from pythonforandroid.util import current_directory
import sh


class PyWebViewRecipe(PythonRecipe):
  """pywebview with a patch for CookieManager.acceptCookie signature.

  Upstream declares acceptCookie = JavaMethod('(Z)V') (copy-paste from
  setAcceptCookie) but the real android.webkit.CookieManager.acceptCookie()
  takes no args and returns boolean → correct signature is '()Z'.
  """

  version = "6.0"
  url = "https://files.pythonhosted.org/packages/source/p/pywebview/pywebview-{version}.tar.gz"
  site_packages_name = "webview"
  depends = ["setuptools"]
  patches = ["patches/fix-acceptcookie-signature.patch"]

  def build_arch(self, arch):
    env = self.get_recipe_env(arch)
    install_dir = self.ctx.get_python_install_dir(arch.arch)
    info(f"Installing patched {self.name} for {arch.arch} via pip")
    with current_directory(self.get_build_dir(arch.arch)):
      sh.Command("pip")(
        "install",
        "--no-deps",
        "--no-build-isolation",
        f"--target={install_dir}",
        ".",
        _env=env,
      )


recipe = PyWebViewRecipe()
