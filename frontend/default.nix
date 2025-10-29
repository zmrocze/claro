{ lib, buildNpmPackage, pkg-config, cairo, pango, pixman, giflib, libjpeg, libpng, librsvg }:

buildNpmPackage {
  pname = "carlo-frontend";
  version = "0.1.0";
  
  src = lib.fileset.toSource {
    root = ./.;
    fileset = lib.fileset.unions [
      ./package.json
      ./package-lock.json
      ./vite.config.ts
      ./tsconfig.json
      ./tsconfig.app.json
      ./tsconfig.node.json
      ./index.html
      ./postcss.config.js
      ./tailwind.config.js
      ./components.json
      ./eslint.config.js
      ./openapi-ts.config.ts
      ./src
      ./public
      ./.env.production
    ];
  };

  # This hash will need to be updated after first build attempt
  # Run: nix build .#frontend 2>&1 | grep "got:" to get the correct hash
  npmDepsHash = "sha256-yUV6NSfMbHSj0EbdX5XP4DoPk3AApT+osMS4PgNMamA=";
  
  # Handle peer dependency conflicts (React 19 vs dependencies expecting React 18)
  # npmFlags = [ "--legacy-peer-deps" ];
  
  # Native dependencies for canvas package
  nativeBuildInputs = [ pkg-config ];
  buildInputs = [ cairo pango pixman libpng giflib libjpeg librsvg ];
  
  # Configure Vite to output to $out directly
  buildPhase = ''
    runHook preBuild
    npm run build -- --outDir $out
    runHook postBuild
  '';
  
  # Skip default install phase since we output directly
  dontInstall = true;
  
  meta = with lib; {
    description = "Carlo AI Assistant - React frontend";
    license = licenses.mit;
    platforms = platforms.all;
  };
}
