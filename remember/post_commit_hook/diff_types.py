"""Structured data types for git commit diffs.

We use unidiff's types (PatchSet, PatchedFile, Hunk, Line) directly for diff data.
This module only adds commit metadata wrapper.
"""

from dataclasses import dataclass
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document
from unidiff import PatchSet


@dataclass
class CommitDiff:
  """Commit metadata with diff data.

  Attributes:
      commit_hash: Full SHA hash of the commit
      author: Author name and email
      timestamp: ISO format timestamp
      message: Commit message
      patch_set: unidiff PatchSet containing all file diffs
  """

  commit_hash: str
  author: str
  timestamp: str
  message: str
  patch_set: PatchSet

  def to_dict(self):
    """Convert to dict for JSON serialization.

    Returns dict with commit metadata and files array.
    Each file includes hunks with lines that have is_added, is_removed fields.
    """
    files = []
    for patched_file in self.patch_set:
      # Skip deleted and renamed files
      if patched_file.is_removed_file or patched_file.is_rename:
        continue

      file_dict = {
        "path": patched_file.path,
        "is_added_file": patched_file.is_added_file,
        "additions": patched_file.added,
        "deletions": patched_file.removed,
        "hunks": [],
      }

      for hunk in patched_file:
        hunk_dict = {
          "source_start": hunk.source_start,
          "source_length": hunk.source_length,
          "target_start": hunk.target_start,
          "target_length": hunk.target_length,
          "lines": [
            {
              "value": line.value,
              "is_added": line.is_added,
              "is_removed": line.is_removed,
              "is_context": line.is_context,
            }
            for line in hunk
          ],
        }
        file_dict["hunks"].append(hunk_dict)

      files.append(file_dict)

    return {
      "commit_hash": self.commit_hash,
      "author": self.author,
      "timestamp": self.timestamp,
      "message": self.message,
      "files": files,
    }

  def iter_new_chunks(self):
    """Iterate over new code chunks (added lines) in the commit.

    Yields:
        NewChunk: Each chunk with filepath and joined added text
    """
    for patched_file in self.patch_set:
      # Skip deleted and renamed files
      if patched_file.is_removed_file or patched_file.is_rename:
        continue

      filepath = Path(patched_file.path)

      for hunk in patched_file:
        # Collect all added lines in this hunk
        added_lines = [line.value for line in hunk if line.is_added]

        if added_lines:
          # Join added lines into single text
          added_text = "".join(added_lines)
          yield NewChunk(filepath=filepath, added_text=added_text)

  def iter_sentence_nodes(self):
    """Iterate over sentence-split nodes from new chunks.

    Uses SentenceSplitter to break down added code into smaller chunks.

    Yields:
        Node: LlamaIndex nodes with sentence-split content
    """
    for chunk in self.iter_new_chunks():
      yield from chunk.iter_sentence_nodes()


@dataclass
class NewChunk:
  """A chunk of newly added code from a git commit."""

  filepath: Path
  added_text: str

  def iter_sentence_nodes(self):
    """Split added_text into sentence-level nodes using SentenceSplitter.

    Yields:
        Node: LlamaIndex nodes with sentence-split content
    """
    # Create a Document from the added text
    doc = Document(
      text=self.added_text,
      metadata={"filepath": str(self.filepath)},
    )

    # Use SentenceSplitter to break into smaller chunks
    splitter = SentenceSplitter(chunk_size=1024, chunk_overlap=200)
    nodes = splitter.get_nodes_from_documents([doc])

    yield from nodes
