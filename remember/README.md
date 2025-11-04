# Git Remember Hook

A git post-commit hook that captures and structures commit diffs for eventual
submission to Zep memory.

## Usage

### Build

```bash
nix build .#git-remember-hook
```

### Install as Post-Commit Hook

Make the git-remember-hook exec run as post-commit git hook.

Now every commit will automatically:

1. Parse the commit diff using GitPython and unidiff
2. Print structured JSON with commit metadata and changes
3. Show a summary of files changed
4. Display new code chunks (added lines)

### Test Manually

```bash
# Run on latest commit without installing
nix run .#git-remember-hook
```

## What It Captures

- **Commit metadata**: hash, author, timestamp, message
- **File changes**: additions/modifications (ignores deletions/renames)
- **Diff hunks**: line-level detail with `is_added`, `is_removed`, `is_context`
  flags
- **New code chunks**: joined added lines per hunk

## Output

1. Full JSON diff structure
2. Summary of changed files
3. New code chunks with file paths

## Architecture

**Design Philosophy**: Use unidiff's types directly instead of creating
redundant wrappers.

- **`diff_types.py`**: Minimal wrapper adding commit metadata
  - `CommitDiff`: Wraps unidiff's `PatchSet` with commit metadata
  - `NewChunk`: Represents added code chunks (filepath + joined added lines)
  - Uses unidiff's `PatchedFile`, `Hunk`, `Line` types directly

- **`diff_parser.py`**: Extracts commit metadata and parses diffs
  - GitPython: Get commit hash, author, timestamp, message
  - Generates unified diff text
  - unidiff: Parse into structured `PatchSet`
  - Handles initial commits (no parent)

- **`main.py`**: Entry point with main() function
  - Parses commit diff
  - Prints JSON representation
  - Shows summary and new code chunks
  - Packaged by Nix as `git-remember-hook` executable

- **`default.nix`**: Nix package
  - Python environment with GitPython and unidiff
  - Installs remember package and main.py
  - Creates wrapped executable

## Dependencies

- **GitPython**: Git repository interaction
- **unidiff**: Unified diff parsing (we use their types directly!)

## Future

- Zep memory integration
- Filter by file patterns
- Configurable output format
