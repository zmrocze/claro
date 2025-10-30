{ lib
, python3
, uv2nix
, pyproject-nix
, pyproject-build-systems
}:

let
  # Load the uv workspace from the project root (parent directory)
  workspace = uv2nix.lib.workspace.loadWorkspace {
    workspaceRoot = ./..;
  };

  # Create overlay from workspace
  overlay = workspace.mkPyprojectOverlay {
    sourcePreference = "wheel";
  };

  # Override for any packages needing special handling
  pyprojectOverrides = final: prev: {
    # Add overrides here if needed for packages with build issues
    
    # proxy-tools is an old package (2014) that needs setuptools to build from sdist
    # It doesn't declare its build system properly in uv.lock
    proxy-tools = prev.proxy-tools.overrideAttrs (old: {
      nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ final.setuptools ];
      propagatedBuildInputs = (old.propagatedBuildInputs or [ ]) ++ [ final.setuptools ];
    });
  };

  # Build Python package set
  pythonSet = (python3.pkgs.callPackage pyproject-nix.build.packages {
    python = python3;
  }).overrideScope (lib.composeManyExtensions [
    pyproject-build-systems.overlays.default
    overlay
    pyprojectOverrides
  ]);

in
  # Build the application virtual environment with all dependencies
  pythonSet.mkVirtualEnv "claro-backend-env" workspace.deps.default
