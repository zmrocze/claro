{ lib
, stdenv
, makeWrapper
, pythonSet
, workspace
, python3
}:

let
  # Build the Python virtual environment with all dependencies
  pythonEnv = pythonSet.mkVirtualEnv "notify-with-carlo-env" workspace.deps.all;

in
stdenv.mkDerivation {
  pname = "notify-with-carlo";
  version = "0.1.0";
  
  dontUnpack = true;
  
  nativeBuildInputs = [ makeWrapper ];
  
  src = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions [
      ./main.py
      ../backend
      ../os_interfaces
    ];
  };
  
  installPhase = ''
    runHook preInstall
    
    mkdir -p $out/bin
    mkdir -p $out/share/notify-with-carlo
    
    # Copy the notification script
    cp $src/notification/main.py $out/share/notify-with-carlo/
    
    # Copy backend and os_interfaces source code
    cp -r $src/backend $out/share/notify-with-carlo/
    cp -r $src/os_interfaces $out/share/notify-with-carlo/
    
    # Create wrapper that uses Python environment
    makeWrapper ${pythonEnv}/bin/python $out/bin/notify-with-carlo \
      --add-flags "$out/share/notify-with-carlo/main.py" \
      --set PYTHONPATH "$out/share/notify-with-carlo:${pythonEnv}/${python3.sitePackages}"
    
    runHook postInstall
  '';
  
  meta = with lib; {
    description = "Carlo notification executable - creates system notifications with AI responses";
    longDescription = ''
      Command-line tool that takes a prompt, runs the Carlo AI agent,
      and creates a system notification with the response.
      Clicking the notification opens an app via deep link.
    '';
    homepage = "https://github.com/zmrocze/claro";
    license = licenses.mit;
    platforms = platforms.linux;
    mainProgram = "notify-with-carlo";
  };
}
