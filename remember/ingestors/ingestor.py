"""Ingestion pipeline components for processing repository files.

This module provides flexible transform components for processing different file types
with LlamaIndex, including conditional transforms based on file extensions and custom
handling for specific files.
"""

import csv
import io
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List, Sequence, Union

from llama_index.core import SimpleDirectoryReader
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import (
  HTMLNodeParser,
  JSONNodeParser,
  MarkdownNodeParser,
  SentenceSplitter,
  SimpleFileNodeParser,
)
from llama_index.core.schema import BaseNode, TextNode, TransformComponent
from llama_index.readers.file import CSVReader


def directory_reader(tracked_file_paths: List[Path]):
  return SimpleDirectoryReader(
    input_files=tracked_file_paths,
    filename_as_id=True,
    file_extractor={
      ".csv": CSVReader()
    },  # PandasCsvReader trims header row, could also just use None here for plain text reader.
  )


@dataclass
class PassThroughError:
  """Raise an error when encountering unknown file types."""

  pass


@dataclass
class PassThroughUnchanged:
  """Pass through unknown file types unchanged."""

  pass


@dataclass
class PassThroughDefault:
  """Apply a default transform to unknown file types.

  Args:
      transform: The default transform to apply
  """

  transform: TransformComponent


PassThroughBehavior = Union[PassThroughError, PassThroughUnchanged, PassThroughDefault]


class ConditionalExtensionTransform(TransformComponent):
  """Transform that applies different transforms based on file extension.

  This transform routes nodes to different processing pipelines based on their
  file extension. File readers (BaseReader) are handled by SimpleDirectoryReader
  before this stage - this only handles node transformations.

  Args:
      extension_transforms: Dict mapping file extensions (e.g., '.md', '.csv') to
          TransformComponent instances that should process those files.
      pass_through_behavior: How to handle unknown extensions:
          - PassThroughError: Raise ValueError
          - PassThroughUnchanged: Pass through unchanged
          - PassThroughDefault(transform): Apply default transform
  """

  # Declare Pydantic fields as class attributes
  extension_transforms: Dict[str, TransformComponent]
  pass_through_behavior: PassThroughBehavior = PassThroughUnchanged()

  def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
    """Apply transforms conditionally based on file extension.

    Args:
        nodes: Input nodes to transform
        **kwargs: Additional arguments passed to child transforms

    Returns:
        Transformed nodes

    Raises:
        ValueError: If pass_through_behavior is PassThroughError and unknown extension encountered
    """
    result_nodes = []

    for node in nodes:
      # Get file extension from metadata
      file_path = node.metadata.get("file_path", "")
      extension = Path(file_path).suffix.lower() if file_path else ""

      # Apply appropriate transform
      if extension in self.extension_transforms:
        handler = self.extension_transforms[extension]
        transformed = handler([node], **kwargs)
        result_nodes.extend(transformed)
      elif isinstance(self.pass_through_behavior, PassThroughUnchanged):
        result_nodes.append(node)
      elif isinstance(self.pass_through_behavior, PassThroughDefault):
        handler = self.pass_through_behavior.transform
        transformed = handler([node], **kwargs)
        result_nodes.extend(transformed)
      elif isinstance(self.pass_through_behavior, PassThroughError):
        raise ValueError(
          f"Unknown file extension '{extension}' for file: {file_path}. "
          f"Known extensions: {list(self.extension_transforms.keys())}"
        )

    return result_nodes


class SkipTransform(TransformComponent):
  """Transform that skips/ignores all nodes.

  This is useful for explicitly ignoring certain file extensions in a pipeline.
  """

  def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
    """Skip all nodes by returning empty list.

    Args:
        nodes: Input nodes (ignored)
        **kwargs: Additional arguments (ignored)

    Returns:
        Empty list
    """
    return []


class LineSplitTransform(TransformComponent):
  """Transform that splits node content into lines.

  This is useful for explicitly ignoring certain file extensions in a pipeline.
  """

  def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
    """Split node content into lines."""
    return [
      TextNode(text=line, metadata=node.metadata)
      for node in nodes
      for line in node.get_content().splitlines()
    ]


class ImageMetadataTransform(TransformComponent):
  """Transform that extracts only title and date metadata from image nodes.

  This transform strips the content from image nodes and keeps only essential metadata.
  """

  def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
    """Extract only title and date from image nodes.

    Args:
        nodes: Input nodes
        **kwargs: Additional arguments (ignored)

    Returns:
        Nodes with only title and date metadata
    """
    result_nodes = []

    for node in nodes:
      # Keep only title and date metadata
      filtered_metadata = {}
      if "title" in node.metadata:
        filtered_metadata["title"] = node.metadata["title"]
      if "date" in node.metadata:
        filtered_metadata["date"] = node.metadata["date"]
      if "file_path" in node.metadata:
        filtered_metadata["file_path"] = node.metadata["file_path"]

      # Create new node with filtered metadata and empty text
      node.metadata = filtered_metadata
      node.set_content(f"[Image: {filtered_metadata.get('title', 'untitled')}]")
      result_nodes.append(node)

    return result_nodes


class ConditionalFilenameTransform(TransformComponent):
  """Transform that applies different transforms based on filename.

  This is similar to ConditionalExtensionTransform but matches on exact filenames
  instead of extensions. Useful for custom handling of specific files.

  Args:
      filename_transforms: Dict mapping filenames to TransformComponent instances
      pass_through_behavior: How to handle unknown filenames:
          - PassThroughError: Raise ValueError
          - PassThroughUnchanged: Pass through unchanged
          - PassThroughDefault(transform): Apply default transform
  """

  # Declare Pydantic fields as class attributes
  filename_transforms: Dict[str, TransformComponent]
  pass_through_behavior: PassThroughBehavior = PassThroughUnchanged()

  def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
    """Apply transforms conditionally based on filename.

    Args:
        nodes: Input nodes to transform
        **kwargs: Additional arguments passed to child transforms

    Returns:
        Transformed nodes

    Raises:
        ValueError: If pass_through_behavior is PassThroughError and unknown filename encountered
    """
    result_nodes = []
    for node in nodes:
      # Get filename from metadata
      file_path = node.metadata.get("file_path", "")
      filename = Path(file_path).name if file_path else ""
      # Apply appropriate transform
      if filename in self.filename_transforms:
        transform = self.filename_transforms[filename]
        transformed = transform([node], **kwargs)
        result_nodes.extend(transformed)
      elif isinstance(self.pass_through_behavior, PassThroughUnchanged):
        result_nodes.append(node)
      elif isinstance(self.pass_through_behavior, PassThroughDefault):
        transform = self.pass_through_behavior.transform
        transformed = transform([node], **kwargs)
        result_nodes.extend(transformed)
      elif isinstance(self.pass_through_behavior, PassThroughError):
        raise ValueError(
          f"Unknown filename '{filename}' for file: {file_path}. "
          f"Known filenames: {list(self.filename_transforms.keys())}"
        )

    return result_nodes


class CSVNodeParser(TransformComponent):
  """Transform that parses a CSV file and creates nodes for each row."""

  def __call__(self, nodes: Sequence[BaseNode], **kwargs) -> Sequence[BaseNode]:
    """Parse CSV content and create nodes for positive dates per category.

    Args:
        nodes: Input nodes containing CSV data
        **kwargs: Additional arguments (ignored)

    Returns:
        List of nodes, one per positive date-category pair
    """
    result_nodes = []
    for node in nodes:
      content = node.get_content()
      if not content:
        raise ValueError("Node content is empty")

      csv_reader = csv.reader(io.StringIO(content))
      rows = list(csv_reader)

      if len(rows) < 2:
        raise ValueError("CSV must have at least 2 rows")

      result_nodes.extend(self._process_csv(rows, node.metadata))

    return result_nodes

  def _process_csv(self, rows: list[list[str]], metadata: dict) -> Sequence[BaseNode]:
    """Process CSV content and create nodes."""

    def not_empty(s: str) -> bool:
      return s != "" and not s.isspace()

    categories = rows[0]
    assert len(categories) > 1

    result_nodes = []
    for row in rows[1:]:
      json_d = {
        cat: val
        for cat, val in zip(categories, row)
        if not_empty(cat) or not_empty(val)
      }
      result_nodes.append(
        TextNode(
          text=json.dumps(json_d),
          metadata=metadata,
        )
      )
    return result_nodes


class CheckmarksCsv(CSVNodeParser):
  """Transform that parses a checkmarks CSV from habits android app format and creates nodes for positive dates.

  Expected CSV format:
  - First row: columns (first column is date, rest are category names)
  - Subsequent rows: date values followed by category counts
  - Count encoding: 2 means count of 1 (positive), -1/0/1 means count of 0 (negative/neutral)

  For each category, this transform collects all dates with count of 1 (value 2)
  and creates a node for each positive date with text "<date>: <category name>".
  """

  def _process_csv(self, rows: list[list[str]], metadata: dict) -> Sequence[BaseNode]:
    """Process CSV content and create nodes for positive dates per category."""
    header = rows[0]
    if len(header) < 3:
      raise ValueError(
        "CSV must have at least 3 columns: date, column, <empty column after trailing comma> "
      )
    categories = header[1:-1]  # Skip date column and trailing empty column
    assert (
      header[-1] == " "
    )  # CSV is expected to have empty column due to trailing comma

    result_nodes = []
    for row in rows[1:]:
      date_value = row[0]
      assert row[-1] == " "
      for cat, val in zip(categories, row[1:]):
        if int(val) == 2:
          result_nodes.append(
            TextNode(
              text=f"{date_value}: {cat}",
              metadata=metadata,
            )
          )
    return result_nodes


def main_ingestion_pipeline(
  enable_custom: bool = False,
  chunk_size: int = 1024,
  chunk_overlap: int = 200,
) -> IngestionPipeline:
  """Create the main ingestion pipeline for repository files.

  This pipeline treats file readers and node parsers uniformly as transforms.
  All file-specific processing is configured in a single extension_transforms dictionary.

  Args:
      enable_custom: If True, enable custom handling for specific files like
          'Cache.txt' and 'Scores.csv'. If False, use standard transforms.
      chunk_size: Size of chunks for sentence splitting (default: 1024)
      chunk_overlap: Overlap between chunks (default: 200)

  Returns:
      Configured IngestionPipeline ready to process documents
  """
  # All node transforms in one place.
  extension_transforms: Dict[str, TransformComponent] = {
    ".md": MarkdownNodeParser(),
    ".html": HTMLNodeParser(),
    ".json": JSONNodeParser(),
    ".csv": ConditionalFilenameTransform(
      filename_transforms={
        "Checkmarks.csv": CheckmarksCsv(),
        "Scores.csv": SkipTransform(),
      }
      if enable_custom
      else {},
      pass_through_behavior=PassThroughDefault(CSVNodeParser()),
    ),
    ".txt": ConditionalFilenameTransform(
      filename_transforms={"Cache.txt": LineSplitTransform()} if enable_custom else {},
      pass_through_behavior=PassThroughDefault(SimpleFileNodeParser()),
    ),
  }

  transformations_list: Sequence[TransformComponent] = [
    ConditionalExtensionTransform(
      extension_transforms=extension_transforms,
      pass_through_behavior=PassThroughDefault(SimpleFileNodeParser()),
    ),
    SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
  ]

  return IngestionPipeline(transformations=list(transformations_list))
