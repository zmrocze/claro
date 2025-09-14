# guide

# Development Environment

This project uses a **Nix + devenv + uv** stack for reproducible development:

Important files:
├── notes/
│   ├── app_technical.md  # for high level architecture plan
│   ├── ux.md             # for basic app usage
|-- nix/devenv.nix        # for nix dependencies
|-- pyproject.toml        # for python deps
      
## Important Rules
1. **Always run Python through uv**: i.e. `uv run script.py`
2. **Never pip install**: Dependencies are managed via `pyproject.toml` or `nix/devenv.nix`
3. **No shebangs in Python files**: python files NEVER start with "#!/usr/bin/env"
4. **run tests**  from file <filename> with: `uv run pytest -k <filename>` and all tests with `uv run pytest`

## Style

1. write short, concise code. if possible avoid declaring every step of calculation as new variable, prefer bigger expression. Prefer functional, pure style. if code snippet repeats, refactor to use a function.
2. never `import` anywhere other than at the top of a file
