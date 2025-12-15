{ lib
, stdenv
, makeWrapper
, pythonSet
, workspace
, python3
}:

let
  # Build the Python virtual environment with all dependencies
  pythonEnv = pythonSet.mkVirtualEnv "claro-notification-scheduler-env" workspace.deps.all;

in
stdenv.mkDerivation {
  pname = "claro-notification-scheduler";
  version = "0.1.0";
  
  dontUnpack = true;
  
  nativeBuildInputs = [ makeWrapper ];
  
  src = lib.fileset.toSource {
    root = ../.;
    fileset = lib.fileset.unions [
      ./.
      ../backend
      ../os_interfaces
    ];
  };
  
  installPhase = ''
    runHook preInstall
    
    mkdir -p $out/bin
    mkdir -p $out/share/claro-notification-scheduler
    
    # Copy the scheduler script
    cp $src/notification_schedule/main.py $out/share/claro-notification-scheduler/
    
    # Copy backend, os_interfaces, and notification_schedule source code
    cp -r $src/backend $out/share/claro-notification-scheduler/
    cp -r $src/os_interfaces $out/share/claro-notification-scheduler/
    cp -r $src/notification_schedule $out/share/claro-notification-scheduler/
    
    # Create wrapper that uses Python environment
    makeWrapper ${pythonEnv}/bin/python $out/bin/claro-notification-scheduler \
      --add-flags "$out/share/claro-notification-scheduler/main.py" \
      --set PYTHONPATH "$out/share/claro-notification-scheduler:${pythonEnv}/${python3.sitePackages}"
    
    runHook postInstall
  '';
  
  meta = with lib; {
    description = "Notification scheduler for Claro";
    license = licenses.mit;
    platforms = platforms.linux;
  };
}
