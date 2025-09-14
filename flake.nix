{
  description = "Hello world flake using uv2nix";

  inputs = {
    nixpkgs.url = "github:cachix/devenv-nixpkgs/rolling";
    # nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    
    flake-parts.url = "github:hercules-ci/flake-parts";
    my-lib.url = "github:zmrocze/nix-lib";
    
    devenv.url = "github:cachix/devenv";

    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        nixpkgs.follows = "nixpkgs";
      };
    };

    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs = {
        pyproject-nix.follows = "pyproject-nix";
        uv2nix.follows = "uv2nix";
        nixpkgs.follows = "nixpkgs";
      };
    };
  };

  outputs =
    inputs@{
      nixpkgs,
      flake-parts,
      my-lib,
      uv2nix,
      pyproject-nix,
      pyproject-build-systems,
      devenv,
      ...
    }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
    in
    flake-parts.lib.mkFlake { inherit inputs; } {
      ### Remember to run like `nix develop --no-pure-eval`, devenv requirement.
      ### 
      imports = [
        my-lib.flakeModules.pkgs
        devenv.flakeModule
        ./nix/devenv.nix
      ];
      inherit systems;
      pkgsConfig.overlays = [
        my-lib.overlays.default
      ];
      perSystem = { pkgs, ... }:
        let
          # myLib = my-lib.lib;
          inherit (nixpkgs) lib;

          # Load a uv workspace from a workspace root.
          # Uv2nix treats all uv projects as workspace projects.
          workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

          # Create package overlay from workspace.
          overlay = workspace.mkPyprojectOverlay {
            # Prefer prebuilt binary wheels as a package source.
            # Sdists are less likely to "just work" because of the metadata missing from uv.lock.
            # Binary wheels are more likely to, but may still require overrides for library dependencies.
            sourcePreference = "wheel"; # or sourcePreference = "sdist";
            # Optionally customise PEP 508 environment
            # environ = {
            #   platform_release = "5.10.65";
            # };
          };

          # Extend generated overlay with build fixups
          #
          # Uv2nix can only work with what it has, and uv.lock is missing essential metadata to perform some builds.
          # This is an additional overlay implementing build fixups.
          # See:
          # - https://pyproject-nix.github.io/uv2nix/FAQ.html
          pyprojectOverrides = _final: _prev: {
            # Implement build fixups here.
            # Note that uv2nix is _not_ using Nixpkgs buildPythonPackage.
            # It's using https://pyproject-nix.github.io/pyproject.nix/build.html
          };

          # Use Python 3.12 from nixpkgs
          python = pkgs.python312;

          # Construct package set
          pythonSet =
            # Use base package set from pyproject.nix builders
            (pkgs.callPackage pyproject-nix.build.packages {
              inherit python;
            }).overrideScope
              (
                lib.composeManyExtensions [
                  pyproject-build-systems.overlays.default
                  overlay
                  pyprojectOverrides
                ]
              );
        in
    {
       # Package a virtual environment as our main application.
      #
      # Enable no optional dependencies for production build.
      packages = {
        default = pythonSet.mkVirtualEnv "hello-world-env" workspace.deps.default;
        this = builtins.trace pythonSet.mkPyprojectPackage workspace.mkPyprojectPackage {
          inherit pkgs;
        };
      };
    };
  };
}
