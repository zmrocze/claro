# Remember - Implementation Summary

## Overview

The `remember` system captures git repository content and commit changes for
memory storage. It consists of two main executables:

1. **post_commit_hook** - Captures commit diffs with sentence-level chunking
2. **remember_repo** - Sets up repositories with the post-commit hook

## Key Features

### 1. Sentence-Level Chunking

Both tools use LlamaIndex's `SentenceSplitter` to break code into smaller,
semantic chunks:

- **Chunk size**: 1024 characters
- **Overlap**: 200 characters
- **Purpose**: Create manageable units for memory storage

### 2. Git Integration

- Uses GitPython for repository interaction
- Uses unidiff for diff parsing (direct type usage, no wrappers)
- Handles initial commits (no parent) correctly

### 3. Selective Capture

- **Ignores**: Deleted files, renamed files
- **Captures**: Added files, modified files
- **Focus**: Only new/changed content (added lines)

## Workflow

### Initial Setup

```bash
# Build the setup tool
nix build .#remember-repo

# Run on a repository
remember-repo /path/to/repo
```

This will:

1. Validate it's a git repository
2. Load all git-tracked files
3. Split them into sentence chunks
4. Display all chunks (for verification)
5. Create `.git/hooks/post-commit` hook

### Post-Commit Capture

After setup, every commit automatically:

1. Parses the commit diff
2. Extracts only added lines
3. Splits added code into sentence chunks
4. Prints structured output with metadata

## Data Structure

### CommitDiff

```python
@dataclass
class CommitDiff:
    commit_hash: str
    author: str
    timestamp: str
    message: str
    patch_set: PatchSet  # unidiff type
    
    def iter_sentence_nodes(self):
        """Yields sentence-split nodes from all new chunks"""
```

### NewChunk

```python
@dataclass
class NewChunk:
    filepath: Path
    added_text: str
    
    def iter_sentence_nodes(self):
        """Yields sentence-split nodes using SentenceSplitter"""
```

## Implementation Details

### Sentence Splitting (diff_types.py)

```python
def iter_sentence_nodes(self):
    doc = Document(
        text=self.added_text,
        metadata={"filepath": str(self.filepath)},
    )
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=200)
    nodes = splitter.get_nodes_from_documents([doc])
    yield from nodes
```

### Directory Splitting (remember_repo/main.py)

```python
def split_directory_into_nodes(repo_path: Path) -> List[BaseNode]:
    # Get git-tracked files
    repo = Repo(repo_path)
    tracked_files = repo.git.ls_files().split("\n")
    
    # Load with SimpleDirectoryReader
    reader = SimpleDirectoryReader(input_files=tracked_file_paths)
    documents = reader.load_data()
    
    # Split with SentenceSplitter
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=200)
    nodes = splitter.get_nodes_from_documents(documents)
    
    return nodes
```

## Configuration Defaults

- **Chunk size**: 1024 characters
- **Chunk overlap**: 200 characters
- **Diff context**: 3 lines (unified diff format)

## Future Enhancements

- Zep memory integration
- Configurable chunk size/overlap
- File pattern filtering
- Incremental updates (only changed files)
