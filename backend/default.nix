{ pythonSet
, workspace
}:

# Build the application virtual environment with all dependencies
pythonSet.mkVirtualEnv "claro-backend-env" workspace.deps.all
