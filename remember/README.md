# Git Remember

A system for capturing git commits and repository content for memory storage.

## Components

### 1. post_commit_hook

A git post-commit hook that captures and structures commit diffs.

**Build:**

```bash
nix build .#git-remember-hook
```

**What it does:**

- Parses commit diffs using GitPython and unidiff
- Splits added code into sentence-level chunks using LlamaIndex SentenceSplitter
- Prints structured output with commit metadata and changes

**Run manually:**

```bash
nix run .#git-remember-hook
```

### 2. remember_repo

A setup tool that installs the post-commit hook in a git repository.

**Build:**

```bash
nix build .#remember-repo
```

**Usage:**

```bash
remember-repo /path/to/git/repo
```

**What it does:**

1. Verifies the path is a git repository
2. Checks if `.git/hooks/post-commit` doesn't already exist
3. Tests directory splitting on all git-tracked files using:
   - SimpleDirectoryReader (loads all tracked files)
   - SentenceSplitter (splits into chunks)
4. Prints all resulting nodes
5. If successful, creates the post-commit hook script

## How It Works

### Post-Commit Hook Flow

1. After each commit, the hook runs automatically
2. Parses the commit diff to extract added lines
3. Uses SentenceSplitter to break added code into smaller chunks
4. Prints each chunk with metadata

### Initial Repository Setup Flow

1. Run `remember-repo /path/to/repo`
2. Loads all git-tracked files
3. Splits them into sentence-level chunks
4. Displays all chunks (validates the splitting works)
5. Creates `.git/hooks/post-commit` that calls `git-remember-hook`

## Data Captured

### From Commits (post_commit_hook)

- **Commit metadata**: hash, author, timestamp, message
- **Added code**: Only new/modified lines (ignores deletions/renames)
- **Sentence chunks**: Added code split into smaller semantic units

### From Repository (remember_repo)

- **All tracked files**: Every file currently in git
- **Sentence chunks**: All content split into smaller semantic units

## Architecture

**Design Philosophy**: Use unidiff's types directly instead of creating
redundant wrappers. Use LlamaIndex for text chunking.

### Directory Structure

```
remember/
├── __init__.py                    # Main package exports
├── post_commit_hook/              # Post-commit hook executable
│   ├── __init__.py
│   ├── diff_types.py              # CommitDiff, NewChunk with sentence splitting
│   ├── diff_parser.py             # Git diff parsing
│   ├── main.py                    # Hook entry point
│   └── default.nix                # Nix package for git-remember-hook
└── remember_repo/                 # Repository setup tool
    ├── __init__.py
    ├── main.py                    # Setup tool entry point
    └── default.nix                # Nix package for remember-repo
```

### post_commit_hook

- **`diff_types.py`**: Minimal wrapper adding commit metadata and chunking
  - `CommitDiff`: Wraps unidiff's `PatchSet` with commit metadata
  - `NewChunk`: Represents added code chunks with sentence splitting
  - `iter_sentence_nodes()`: Uses LlamaIndex SentenceSplitter for chunking
  - Uses unidiff's `PatchedFile`, `Hunk`, `Line` types directly

- **`diff_parser.py`**: Extracts commit metadata and parses diffs
  - GitPython: Get commit hash, author, timestamp, message
  - Generates unified diff text
  - unidiff: Parse into structured `PatchSet`
  - Handles initial commits (no parent)

- **`main.py`**: Entry point for post-commit hook
  - Parses commit diff
  - Prints JSON representation
  - Shows summary and sentence-split nodes
  - Packaged by Nix as `git-remember-hook` executable

### remember_repo

- **`main.py`**: Setup tool for installing hooks
  - Validates git repository
  - Checks for existing hooks
  - Tests directory splitting with SimpleDirectoryReader + SentenceSplitter
  - Creates `.git/hooks/post-commit` script
  - Packaged by Nix as `remember-repo` executable

## Dependencies

- **GitPython**: Git repository interaction
- **unidiff**: Unified diff parsing (we use their types directly!)
- **LlamaIndex**: Text chunking with SentenceSplitter and SimpleDirectoryReader

## Future

- Zep memory integration
- Filter by file patterns
- Configurable output format
