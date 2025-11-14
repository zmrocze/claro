"""Structured data types for git commit diffs.

We use unidiff's types (PatchSet, PatchedFile, Hunk, Line) directly for diff data.
This module only adds commit metadata wrapper.
"""

from dataclasses import dataclass
from pathlib import Path
import re
import csv
import io

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document
from unidiff import PatchSet

from remember.ingestors.ingestor import main_ingestion_pipeline

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

    if current_headers is None or line_headers == current_headers:
      # Same header context, add to current group
      current_group.append((line_no, line_value))
      current_headers = line_headers
    else:
      # Different header context, yield current group and start new one
      if current_group:
        yield yield_group(current_group)

      # Start new group
      current_group = [(line_no, line_value)]
      current_headers = line_headers

  # Yield the final group
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
      enable_custom: If True, enable custom handling for specific files
  """

  commit_hash: str
  author: str
  timestamp: str
  message: str
  patch_set: PatchSet
  enable_custom: bool = False

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

    Applies file-type-specific transformations:
    - Markdown files: groups lines by header context
    - Other files: yields all added lines as single chunks

    Yields:
        NewChunk: Each chunk with filepath, added text, and optional metadata
    """
    for patched_file in self.patch_set:
      if patched_file.is_removed_file or patched_file.is_rename:
        continue

      filepath = Path(patched_file.path)

      for hunk in patched_file:
        added_lines_with_nos = [
          (line.target_line_no, line.value)
          for line in hunk
          if line.is_added and line.target_line_no
        ]

        if added_lines_with_nos:
          yield from self._process_hunk_by_file_type(filepath, added_lines_with_nos)

  def _process_hunk_by_file_type(
    self, filepath: Path, added_lines_with_nos: list[tuple[int, str]]
  ):
    """Process added lines based on file extension.

    Args:
        filepath: Path to the file
        added_lines_with_nos: List of (line_number, line_value) tuples

    Yields:
        NewChunk: Processed chunks based on file type
    """
    if filepath.suffix.lower() in (".md", ".markdown"):
      yield from self._process_markdown_hunk(filepath, added_lines_with_nos)
    elif filepath.suffix.lower() == ".csv":
      yield from self._process_csv_hunk(filepath, added_lines_with_nos)
    elif (
      filepath.suffix.lower() == ".txt"
      and self.enable_custom
      and filepath.name == "Cache.txt"
    ):
      yield from self._process_cache_txt_hunk(filepath, added_lines_with_nos)
    else:
      yield from self._process_generic_hunk(filepath, added_lines_with_nos)

  def _process_markdown_hunk(
    self, filepath: Path, added_lines_with_nos: list[tuple[int, str]]
  ):
    """Process markdown file hunk by grouping lines by header context."""
    if not filepath.exists():
      yield from self._process_generic_hunk(filepath, added_lines_with_nos)
      return

    try:
      file_content = filepath.read_text(encoding="utf-8")
      yield from _group_markdown_lines_by_headers(
        filepath, file_content, added_lines_with_nos
      )
    except Exception:
      logger.warning(
        f"Failed to process markdown headers for {filepath}, falling back to generic processing"
      )
      yield from self._process_generic_hunk(filepath, added_lines_with_nos)

  def _process_generic_hunk(
    self, filepath: Path, added_lines_with_nos: list[tuple[int, str]]
  ):
    """Process generic file hunk by yielding all added lines as a single chunk."""
    yield NewChunk(
      filepath=filepath,
      added_text="".join(value for _, value in added_lines_with_nos),
      extra_metadata=None,
    )

  def _process_csv_hunk(
    self, filepath: Path, added_lines_with_nos: list[tuple[int, str]]
  ):
    """Process CSV file hunk.

    If the header row changed, process the entire file.
    Otherwise, process only the added/changed rows as JSON.
    """

    try:
      changed_line_numbers = {line_no for line_no, _ in added_lines_with_nos}
      header_changed = 1 in changed_line_numbers

      if header_changed:
        yield from self._process_entire_csv_file(filepath)
      else:
        yield from self._process_csv_rows(filepath, added_lines_with_nos)
    except Exception:
      logger.warning(
        f"Failed to process CSV file {filepath}, falling back to generic processing"
      )
      yield from self._process_generic_hunk(filepath, added_lines_with_nos)

  def _process_entire_csv_file(self, filepath: Path):
    """Process entire CSV file when header has changed."""
    file_content = filepath.read_text(encoding="utf-8")
    yield from self._process_csv_content(file_content, filepath)

  def _process_csv_rows(
    self, filepath: Path, added_lines_with_nos: list[tuple[int, str]]
  ):
    """Process individual CSV rows using ingestor pipeline.

    Constructs single CSV document with header + all changed rows.
    """
    file_content = filepath.read_text(encoding="utf-8")
    csv_reader = csv.reader(io.StringIO(file_content))
    rows = list(csv_reader)

    if len(rows) < 1:
      return

    header = rows[0]

    if not added_lines_with_nos:
      return

    # Construct single CSV with header + all changed rows
    csv_output = io.StringIO()
    writer = csv.writer(csv_output)
    writer.writerow(header)

    for _, line_value in added_lines_with_nos:
      row = next(csv.reader([line_value]))
      writer.writerow(row)

    csv_content = csv_output.getvalue()
    yield from self._process_csv_content(csv_content, filepath)

  def _process_csv_content(self, csv_content: str, filepath: Path):
    """Process CSV content using main_ingestion_pipeline."""
    doc = Document(
      text=csv_content,
      metadata={"file_path": str(filepath), "file_name": filepath.name},
    )

    pipeline = main_ingestion_pipeline(
      enable_custom=self.enable_custom, chunk_size=1024, chunk_overlap=0
    )
    nodes = pipeline.run(documents=[doc])

    for node in nodes:
      yield NewChunk(
        filepath=filepath,
        added_text=node.get_content(),
        extra_metadata=None,
      )

  def _process_cache_txt_hunk(
    self, filepath: Path, added_lines_with_nos: list[tuple[int, str]]
  ):
    """Process Cache.txt file by splitting into individual lines."""
    for _, line_value in added_lines_with_nos:
      if line_value.strip():
        yield NewChunk(
          filepath=filepath,
          added_text=line_value,
          extra_metadata=None,
        )

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
