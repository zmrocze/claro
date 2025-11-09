"""Structured data types for git commit diffs.

We use unidiff's types (PatchSet, PatchedFile, Hunk, Line) directly for diff data.
This module only adds commit metadata wrapper.
"""

from dataclasses import dataclass
from pathlib import Path
import re

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document
from unidiff import PatchSet

import logging

logger = logging.getLogger(__name__)


def _extract_markdown_headers(
  file_content: str, line_numbers: set[int]
) -> dict[int, list[str]]:
  """Extract markdown headers for given line numbers using line-by-line parsing.

  Args:
      file_content: The full markdown file content
      line_numbers: Set of line numbers (1-indexed) to find headers for

  Returns:
      Dict mapping line numbers to lists of header strings (from top-level to immediate parent)
  """
  if not line_numbers:
    return {}

  # Regex for ATX-style headers (# Header)
  header_pattern = re.compile(r"^(#{1,9})\s+(.+?)(?:\s*#*\s*)?$")

  # Track header stack and whether we're in a code block
  header_stack = []  # List of (level, title)
  in_code_block = False
  line_to_headers = {}

  lines = file_content.splitlines()

  for line_num, line in enumerate(lines, start=1):
    # Check for code fence
    if line.strip().startswith("```") or line.strip().startswith("~~~"):
      in_code_block = not in_code_block
      if line_num in line_numbers:
        line_to_headers[line_num] = [h[1] for h in header_stack]
      continue

    # Skip lines inside code blocks
    if in_code_block:
      if line_num in line_numbers:
        line_to_headers[line_num] = [h[1] for h in header_stack]
      continue

    # Check if this line is a header
    match = header_pattern.match(line)
    if match:
      level = len(match.group(1))  # Number of # symbols
      title = match.group(2).strip()

      # Pop headers from stack that are at same or deeper level
      while header_stack and header_stack[-1][0] >= level:
        header_stack.pop()

      # Add this header to stack
      header_stack.append((level, title))

    # Map this line to current header stack
    if line_num in line_numbers:
      line_to_headers[line_num] = [h[1] for h in header_stack]

  return line_to_headers


def _group_markdown_lines_by_headers(
  filepath, file_content: str, added_lines_with_nos: list[tuple[int, str]]
):
  """Group consecutive added lines by their markdown header context.

  Args:
      filepath: Path to the markdown file
      file_content: Full content of the markdown file
      added_lines_with_nos: List of (line_number, line_value) tuples

  Yields:
      NewChunk: Chunks grouped by header context
  """
  line_numbers = {line_no for line_no, _ in added_lines_with_nos}
  line_to_headers = _extract_markdown_headers(file_content, line_numbers)

  def yield_group(group):
    """Helper to yield a NewChunk from a group of lines."""
    logger.info("Yielding group of lines")
    added_text = "".join(value for _, value in group)
    extra_metadata = {
      "header_path": "/" + "/".join(list(line_to_headers.get(group[0][0], [])))
    }
    return NewChunk(
      filepath=filepath, added_text=added_text, extra_metadata=extra_metadata
    )

  # Group consecutive lines with the same header context
  current_group = []
  current_headers = None

  for line_no, line_value in added_lines_with_nos:
    line_headers = tuple(line_to_headers.get(line_no, []))
    logger.info(f"Line {line_no} has headers {line_headers}")

    if current_headers is None or line_headers == current_headers:
      # Same header context, add to current group
      logger.info("Same header context, adding to current group")
      current_group.append((line_no, line_value))
      current_headers = line_headers
    else:
      # Different header context, yield current group and start new one
      logger.info("Different header context, yielding current group")
      if current_group:
        yield yield_group(current_group)

      # Start new group
      logger.info("Starting new group")
      current_group = [(line_no, line_value)]
      current_headers = line_headers

  # Yield the final group
  logger.info("Yielding final group")
  if current_group:
    yield yield_group(current_group)


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

    For markdown files, extracts header information for added/changed lines.

    Yields:
        NewChunk: Each chunk with filepath, added text, and optional metadata
    """
    print("iter_new_chunks")
    for patched_file in self.patch_set:
      # Skip deleted and renamed files
      if patched_file.is_removed_file or patched_file.is_rename:
        continue

      filepath = Path(patched_file.path)
      is_markdown = filepath.suffix.lower() in (".md", ".markdown")

      # For markdown files, read the current file content and collect line numbers
      file_content = None
      if is_markdown and filepath.exists():
        try:
          file_content = filepath.read_text(encoding="utf-8")
        except Exception:
          # If we can't read the file, proceed without markdown metadata
          file_content = None
          logger.warning(f"Failed to read file content for {filepath}")

      for hunk in patched_file:
        # Collect added lines with their line numbers (preserving order)
        added_lines_with_nos = []
        for line in hunk:
          if line.is_added and line.target_line_no:
            added_lines_with_nos.append((line.target_line_no, line.value))

        if not added_lines_with_nos:
          continue

        # For non-markdown files, yield all added lines as a single chunk
        if not is_markdown or not file_content:
          added_text = "".join(value for _, value in added_lines_with_nos)
          yield NewChunk(filepath=filepath, added_text=added_text, extra_metadata=None)
          continue

        # For markdown files, group consecutive lines by header context
        try:
          yield from _group_markdown_lines_by_headers(
            filepath, file_content, added_lines_with_nos
          )
        except Exception:
          logger.warning("Failed to extract markdown headers for diff.")
          # If markdown parsing fails, yield all lines as a single chunk without metadata
          added_text = "".join(value for _, value in added_lines_with_nos)
          yield NewChunk(filepath=filepath, added_text=added_text, extra_metadata=None)

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
  """A chunk of newly added code from a git commit.

  Attributes:
      filepath: Path to the file
      added_text: The added text content
      extra_metadata: Optional metadata (e.g., markdown headers for the added lines)
  """

  filepath: Path
  added_text: str
  extra_metadata: dict[str, str] | None = None

  def iter_sentence_nodes(self):
    """Split added_text into sentence-level nodes using SentenceSplitter.

    Yields:
        Node: LlamaIndex nodes with sentence-split content
    """
    # Create a Document from the added text
    doc = Document(
      text=self.added_text,
      metadata={"file_path": str(self.filepath)} | (self.extra_metadata or {}),
    )

    # Use SentenceSplitter to break into smaller chunks
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=300)
    nodes = splitter.get_nodes_from_documents([doc])
    yield from nodes
