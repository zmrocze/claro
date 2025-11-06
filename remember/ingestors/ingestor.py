"""Ingestion pipeline components for processing repository files.

This module provides flexible transform components for processing different file types
with LlamaIndex, including conditional transforms based on file extensions and custom
handling for specific files.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Sequence, Union

from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import (
  HTMLNodeParser,
  JSONNodeParser,
  MarkdownNodeParser,
  SentenceSplitter,
  SimpleFileNodeParser,
  TokenTextSplitter,
)
from llama_index.core.schema import BaseNode, TransformComponent
from llama_index.core.readers.base import BaseReader
from llama_index.readers.file import DocxReader, PandasCSVReader, PDFReader

logger = logging.getLogger(__name__)


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
  """Abstract transform that applies different transforms based on file extension.

  This transform routes nodes to different processing pipelines based on their
  file extension. Supports both file readers (BaseReader) and node parsers
  (TransformComponent) uniformly.

  Args:
      extension_transforms: Dict mapping file extensions (e.g., '.md', '.csv') to
          readers or transforms that should process those files.
      pass_through_behavior: How to handle unknown extensions:
          - PassThroughError: Raise ValueError
          - PassThroughUnchanged: Pass through unchanged
          - PassThroughDefault(transform): Apply default transform
  """

  def __init__(
    self,
    extension_transforms: Dict[str, Union[BaseReader, TransformComponent]],
    pass_through_behavior: PassThroughBehavior = PassThroughUnchanged(),
  ):
    self.extension_transforms = extension_transforms
    self.pass_through_behavior = pass_through_behavior

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

      # Apply appropriate transform or reader
      if extension in self.extension_transforms:
        handler = self.extension_transforms[extension]
        # Check if it's a BaseReader or TransformComponent
        if isinstance(handler, BaseReader):
          # BaseReaders work on file paths, not nodes
          # In a pipeline, they should have already converted to documents
          # So we just pass through the node unchanged
          result_nodes.append(node)
        else:
          # It's a TransformComponent with __call__
          transformed = handler([node], **kwargs)
          result_nodes.extend(transformed)
      elif isinstance(self.pass_through_behavior, PassThroughUnchanged):
        result_nodes.append(node)
      elif isinstance(self.pass_through_behavior, PassThroughDefault):
        handler = self.pass_through_behavior.transform
        if isinstance(handler, BaseReader):
          result_nodes.append(node)
        else:
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

  def __init__(
    self,
    filename_transforms: Dict[str, TransformComponent],
    pass_through_behavior: PassThroughBehavior = PassThroughUnchanged(),
  ):
    self.filename_transforms = filename_transforms
    self.pass_through_behavior = pass_through_behavior

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
  # All transforms - both file readers and node parsers - in one place.
  # File readers (PDFReader, DocxReader, etc.) and node parsers are treated uniformly.
  extension_transforms: Dict[str, Union[BaseReader, TransformComponent]] = {
    # Specialized node parsers
    ".md": MarkdownNodeParser(),
    ".html": HTMLNodeParser(),
    ".json": JSONNodeParser(),
    # File readers for document formats
    ".docx": DocxReader(),
    ".csv": PandasCSVReader(),
    ".pdf": PDFReader(),
    # Image extensions - extract only metadata, not content
    ".jpg": ImageMetadataTransform(),
    ".jpeg": ImageMetadataTransform(),
    ".png": ImageMetadataTransform(),
    ".gif": ImageMetadataTransform(),
    ".bmp": ImageMetadataTransform(),
    ".svg": ImageMetadataTransform(),
    ".webp": ImageMetadataTransform(),
  }

  # Build and return transformation pipeline as single expression
  transformations_list: Sequence[TransformComponent] = (
    [
      ConditionalExtensionTransform(
        extension_transforms=extension_transforms,
        pass_through_behavior=PassThroughDefault(SimpleFileNodeParser()),
      ),
    ]
    + (
      [
        ConditionalFilenameTransform(
          filename_transforms={
            "Cache.txt": TokenTextSplitter(separator="\n", chunk_size=1),
            "Scores.csv": SkipTransform(),
          },
          pass_through_behavior=PassThroughUnchanged(),
        )
      ]
      if enable_custom
      else []
    )
    + [
      SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap),
    ]
  )

  return IngestionPipeline(transformations=list(transformations_list))
