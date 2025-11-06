# Repository Ingestion Pipeline

This module provides a flexible and extensible ingestion pipeline for processing
repository files with LlamaIndex.

## Architecture

The ingestion system is built around the `TransformComponent` interface from
LlamaIndex, which allows chaining multiple transformations in a pipeline.

### Core Components

#### 1. `ConditionalExtensionTransform`

An abstract transform that routes nodes to different processing pipelines based
on file extension.

**Features:**

- Maps file extensions (`.md`, `.html`, `.json`, etc.) to specific transform
  components
- Three configurable behaviors for unknown extensions:
  - `PassThroughError()`: Raise ValueError
  - `PassThroughUnchanged()`: Pass through unchanged
  - `PassThroughDefault(transform)`: Apply a default transform

**Example:**

```python
# Pass through unknown extensions unchanged
transform = ConditionalExtensionTransform(
    extension_transforms={
        ".md": MarkdownNodeParser(),
        ".html": HTMLNodeParser(),
        ".json": JSONNodeParser(),
    },
    pass_through_behavior=PassThroughUnchanged()
)

# Apply default transform to unknown extensions
transform = ConditionalExtensionTransform(
    extension_transforms={
        ".md": MarkdownNodeParser(),
    },
    pass_through_behavior=PassThroughDefault(SimpleFileNodeParser())
)

# Raise error on unknown extensions
transform = ConditionalExtensionTransform(
    extension_transforms={
        ".md": MarkdownNodeParser(),
    },
    pass_through_behavior=PassThroughError()
)
```

#### 2. `SkipTransform`

A simple transform that ignores/skips all nodes by returning an empty list.

**Use case:** Explicitly ignore certain file types in the pipeline.

**Example:**

```python
# Skip all CSV files
transform = ConditionalExtensionTransform(
    extension_transforms={
        ".csv": SkipTransform(),
    }
)
```

#### 3. `ImageMetadataTransform`

Extracts only title and date metadata from image files, replacing content with a
placeholder.

**Use case:** Include image files in the index without storing full binary
content.

**Example:**

```python
transform = ConditionalExtensionTransform(
    extension_transforms={
        ".jpg": ImageMetadataTransform(),
        ".png": ImageMetadataTransform(),
    }
)
```

#### 4. Line-by-Line Processing

For line-by-line processing, use LlamaIndex's built-in `TokenTextSplitter` with
newline separator.

**Use case:** Process files line-by-line (e.g., log files, cache files).

**Example:**

```python
# Process Cache.txt line by line
transform = ConditionalFilenameTransform(
    filename_transforms={
        "Cache.txt": TokenTextSplitter(separator="\n", chunk_size=1),
    }
)
```

#### 5. `ConditionalFilenameTransform`

Similar to `ConditionalExtensionTransform` but matches on exact filenames
instead of extensions.

**Use case:** Custom handling for specific files (e.g., `Cache.txt`,
`Scores.csv`).

**Example:**

```python
# With pass-through unchanged
transform = ConditionalFilenameTransform(
    filename_transforms={
        "Cache.txt": TokenTextSplitter(separator="\n", chunk_size=1),
        "Scores.csv": SkipTransform(),
    },
    pass_through_behavior=PassThroughUnchanged()
)

# With default transform
transform = ConditionalFilenameTransform(
    filename_transforms={
        "special.txt": TokenTextSplitter(separator="\n", chunk_size=1),
    },
    pass_through_behavior=PassThroughDefault(SimpleFileNodeParser())
)
```

#### 6. `RepositoryIngestor`

The main ingestion pipeline that combines all transforms.

**Features:**

- Handles common file types with specialized parsers:
  - Markdown files: `MarkdownNodeParser`
  - HTML files: `HTMLNodeParser` (extracts specific tags)
  - JSON files: `JSONNodeParser`
  - Document files (`.docx`, `.pdf`, `.doc`): `SimpleFileNodeParser`
  - CSV files: `SimpleFileNodeParser`
  - Code files (`.py`, `.js`, `.ts`, `.tsx`, `.jsx`): `SimpleFileNodeParser`
  - Config files (`.yaml`, `.toml`, `.xml`): `SimpleFileNodeParser`
  - Images: `ImageMetadataTransform` (metadata only)
- Default behavior for unknown extensions:
  `PassThroughDefault(SimpleFileNodeParser())`
- Optional custom handling for specific files (enabled via `enable_custom` flag)
- Configurable chunk size and overlap for sentence splitting
- Final sentence splitting applied to all nodes

**Example:**

```python
# Standard usage
ingestor = RepositoryIngestor(
    enable_custom=False,
    chunk_size=1024,
    chunk_overlap=200
)
nodes = ingestor.process_documents(documents)

# With custom handling
ingestor = RepositoryIngestor(
    enable_custom=True,  # Enables Cache.txt and Scores.csv handling
    chunk_size=1024,
    chunk_overlap=200
)
nodes = ingestor.process_documents(documents)
```

## Pipeline Flow

The ingestion pipeline processes documents in the following order:

1. **Extension-based routing** (`ConditionalExtensionTransform`)
   - Routes nodes to appropriate parsers based on file extension
   - Markdown → `MarkdownNodeParser`
   - HTML → `HTMLNodeParser`
   - JSON → `JSONNodeParser`
   - Documents (DOCX, PDF, DOC) → `SimpleFileNodeParser`
   - CSV → `SimpleFileNodeParser`
   - Code/config → `SimpleFileNodeParser`
   - Images → `ImageMetadataTransform`
   - Unknown → `PassThroughDefault(SimpleFileNodeParser())`

2. **Filename-based routing** (if `enable_custom=True`)
   - `Cache.txt` → `TokenTextSplitter(separator="\n", chunk_size=1)`
     (line-by-line)
   - `Scores.csv` → `SkipTransform` (ignored)
   - Other files → `PassThroughUnchanged()`

3. **Sentence splitting** (`SentenceSplitter`)
   - Splits all nodes into sentence-level chunks
   - Configurable chunk size and overlap
   - Applied to all nodes regardless of file type

## Usage in main.py

The module is integrated into `remember_repo/main.py`:

```python
from remember.ingestors import RepositoryIngestor

# Get file extractors for specialized file reading
file_extractor = RepositoryIngestor.get_file_extractors()

# Load documents with specialized readers
documents = SimpleDirectoryReader(
    input_files=tracked_file_paths,
    file_extractor=file_extractor,
).load_data()

# Process through pipeline
ingestor = RepositoryIngestor(
    enable_custom=args.custom,  # From --custom CLI flag
    chunk_size=1024,
    chunk_overlap=200,
)
nodes = ingestor.process_documents(documents)
```

### Command-line Usage

```bash
# Standard processing
python -m remember.remember_repo.main /path/to/repo

# With custom file handling
python -m remember.remember_repo.main /path/to/repo --custom
```

## Design Principles

### 1. DRY (Don't Repeat Yourself)

- Reusable transform components
- Single definition of file type handling
- Composable pipeline architecture

### 2. Extensibility

- Easy to add new file types by extending `extension_transforms` dict
- Easy to add custom file handling via `filename_transforms` dict
- All transforms implement the same `TransformComponent` interface

### 3. Configurability

- Three pass-through behaviors: Error, Unchanged, or Default transform
- Optional custom handling for specific files
- Configurable chunking parameters
- Specialized parsers for different file types

### 4. Separation of Concerns

- Extension-based routing separate from filename-based routing
- Each transform has a single responsibility
- Pipeline orchestration separate from individual transforms

## Adding New File Types

To add support for a new file type:

1. **Add to extension_transforms in `RepositoryIngestor._build_pipeline()`:**

```python
extension_transforms = {
    # ... existing entries ...
    ".rs": SimpleFileNodeParser(),  # Rust files
    ".go": SimpleFileNodeParser(),  # Go files
    ".rb": SimpleFileNodeParser(),  # Ruby files
}
```

2. **Or create a custom transform for special handling:**

```python
class RustDocTransform(TransformComponent):
    def __call__(self, nodes, **kwargs):
        # Custom processing for Rust files
        return processed_nodes

extension_transforms = {
    ".rs": RustDocTransform(),
}
```

3. **Use PassThroughDefault for automatic handling:**

```python
# All unknown extensions will use SimpleFileNodeParser
transform = ConditionalExtensionTransform(
    extension_transforms=extension_transforms,
    pass_through_behavior=PassThroughDefault(SimpleFileNodeParser())
)
```

## Testing

The pipeline can be tested by running the main script on a repository:

```bash
python -m remember.remember_repo.main /path/to/test/repo --custom
```

This will:

1. Load all git-tracked files
2. Process them through the ingestion pipeline
3. Print all resulting nodes with metadata
4. Install the post-commit hook if successful
