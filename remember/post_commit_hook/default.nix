{ lib
, stdenv
, makeWrapper
, pythonSet
, workspace
, python3
}:

let
  # Build the Python virtual environment with all dependencies
  pythonEnv = pythonSet.mkVirtualEnv "git-remember-hook-env" workspace.deps.all;

in
stdenv.mkDerivation {
  pname = "git-remember-hook";
  version = "0.1.0";
  
  dontUnpack = true;
  
  nativeBuildInputs = [ makeWrapper ];
  
  src = lib.fileset.toSource {
    root = ../..;
    fileset = lib.fileset.unions [
      ./.
    ];
  };
  
  installPhase = ''
    runHook preInstall
    
    mkdir -p $out/bin
    mkdir -p $out/share/git-remember-hook
    
    # Copy the main script
    cp $src/remember/post_commit_hook/main.py $out/share/git-remember-hook/
    
    # Copy post_commit_hook package source code
    cp -r $src/remember/post_commit_hook $out/share/git-remember-hook/
    
    # Create wrapper that uses Python environment
    makeWrapper ${pythonEnv}/bin/python $out/bin/git-remember-hook \
      --add-flags "$out/share/git-remember-hook/main.py" \
      --set PYTHONPATH "$out/share/git-remember-hook:${pythonEnv}/${python3.sitePackages}"
    
    runHook postInstall
  '';
  
  meta = with lib; {
    description = "Git post-commit hook to capture and structure commit diffs for memory storage";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
