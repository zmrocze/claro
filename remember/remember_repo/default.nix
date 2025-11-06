{ lib
, stdenv
, makeWrapper
, pythonSet
, workspace
, python3
}:

let
  # Build the Python virtual environment with all dependencies
  pythonEnv = pythonSet.mkVirtualEnv "remember-repo-env" workspace.deps.all;

in
stdenv.mkDerivation {
  pname = "remember-repo";
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
    mkdir -p $out/share/remember-repo
    
    # Copy the main script
    cp $src/remember/remember_repo/main.py $out/share/remember-repo/
    
    # Copy remember_repo package source code
    cp -r $src/remember/remember_repo $out/share/remember-repo/
    
    # Create wrapper that uses Python environment
    makeWrapper ${pythonEnv}/bin/python $out/bin/remember-repo \
      --add-flags "$out/share/remember-repo/main.py" \
      --set PYTHONPATH "$out/share/remember-repo:${pythonEnv}/${python3.sitePackages}"
    
    runHook postInstall
  '';
  
  meta = with lib; {
    description = "Setup tool for installing git-remember post-commit hooks";
    license = licenses.mit;
    platforms = platforms.unix;
  };
}
