{ symlinkJoin, remember-repo, git-remember-hook }:

symlinkJoin {
  name = "remember-tools";
  paths = [ remember-repo git-remember-hook ];
}