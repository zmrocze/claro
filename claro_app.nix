{ lib
, stdenv
, makeWrapper
, wrapGAppsHook
, gobject-introspection
, gtk3
, webkitgtk_4_1
, gst_all_1
, frontend
, backend
, python3
}:

stdenv.mkDerivation {
  pname = "claro";
  version = "0.1.0";
  
  # We don't need to unpack anything - we're just assembling components
  dontUnpack = true;
  
  nativeBuildInputs = [ 
    makeWrapper
    gobject-introspection  # Required: enables Python bindings to GTK
    wrapGAppsHook # Required: sets up GTK environment variables
  ];
  
  buildInputs = [
    gtk3              # Required: GTK library itself
    webkitgtk_4_1     # Required: WebKit2 rendering engine (v2.22+)
    gobject-introspection  # Required: also needed here for typelibs
    gst_all_1.gstreamer
    gst_all_1.gst-plugins-base
    gst_all_1.gst-plugins-good
    gst_all_1.gst-plugins-bad # (includes fdk-aac)
  ];

  # Copy the claro_app.py script from the source
  src = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./claro_app.py
      ./backend
    ];
  };
  
  buildPhase = ''
    runHook preBuild
    
    # Copy the application entry point script
    cp $src/claro_app.py app.py
    
    # Substitute the frontend path placeholder
    substituteInPlace app.py \
      --replace-fail '@FRONTEND_PATH@' "$out/share/claro/frontend"
    
    runHook postBuild
  '';
  
  installPhase = ''
    runHook preInstall
    
    mkdir -p $out/bin
    mkdir -p $out/share/claro/frontend
    mkdir -p $out/share/claro/backend
    
    # Copy frontend assets
    cp -r ${frontend}/* $out/share/claro/frontend/
    
    # Copy backend source code
    cp -r $src/backend/* $out/share/claro/backend/
    
    # Install the application entry point script
    cp app.py $out/share/claro/
    
    # Create wrapper script that uses backend's Python environment
    # The wrapper sets PYTHONPATH to include the backend code
    makeWrapper ${backend}/bin/python $out/bin/claro \
      --add-flags "$out/share/claro/app.py" \
      --set PYTHONPATH "$out/share/claro:${backend}/${python3.sitePackages}:${python3.pkgs.pygobject3}/${python3.sitePackages}:${python3.pkgs.pycairo}/${python3.sitePackages}"
    
    runHook postInstall
  '';
  
  meta = with lib; {
    description = "Claro AI Assistant - Desktop application";
    longDescription = ''
      Claro is a personal AI assistant with a chat interface and notifications.
      It combines a FastAPI backend with a React frontend, packaged as a
      desktop application using pywebview.
    '';
    homepage = "https://github.com/zmrocze/claro";
    license = licenses.mit;
    platforms = platforms.linux;
    mainProgram = "claro";
  };
}
