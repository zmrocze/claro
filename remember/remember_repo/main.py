#!/usr/bin/env python3
"""Setup git repository with remember post-commit hook.

This script:
1. Verifies the target directory is a git repository
2. Checks if post-commit hook doesn't already exist
3. Tests directory splitting with LlamaIndex on git-tracked files
4. If successful, installs the post-commit hook
"""

import argparse
import logging
import stat
import sys
import traceback
from pathlib import Path
from typing import Sequence

from git import Repo
from git.exc import InvalidGitRepositoryError
from llama_index.core import SimpleDirectoryReader
from llama_index.core.schema import BaseNode

from remember.ingestors import main_ingestion_pipeline

# Configure logging
logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_and_split_repo(
  repo_path: Path, enable_custom: bool = False
) -> Sequence[BaseNode]:
  """Load git-tracked files and split into LlamaIndex nodes.

  Args:
      repo_path: Path to git repository
      enable_custom: Enable custom handling for specific files

  Returns:
      List of LlamaIndex nodes from ingestion pipeline
  """
  logger.info(f"Loading git-tracked files from {repo_path}")

  # Get list of git-tracked files as Path objects
  repo = Repo(repo_path)
  tracked_file_paths = [repo_path / f for f in repo.git.ls_files().splitlines() if f]

  logger.info(f"Found {len(tracked_file_paths)} tracked files")

  # Load documents - all file type handling is now in the transform pipeline
  documents = SimpleDirectoryReader(
    input_files=tracked_file_paths,
    filename_as_id=True,
  ).load_data()

  logger.info(f"Loaded {len(documents)} documents")

  # Process through ingestion pipeline
  logger.info(f"Processing {len(documents)} documents through ingestion pipeline")
  pipeline = main_ingestion_pipeline(
    enable_custom=enable_custom,
    chunk_size=1024,
    chunk_overlap=200,
  )
  nodes = pipeline.run(documents=documents)
  logger.info(f"Created {len(nodes)} nodes from ingestion pipeline")

  return nodes


def create_post_commit_hook(repo_path: Path) -> None:
  """Create post-commit hook that runs git-remember-hook.

  Args:
      repo_path: Path to git repository
  """
  hook_path = repo_path / ".git" / "hooks" / "post-commit"

  # Create the hook script
  hook_content = """#!/usr/bin/env bash
      # Auto-generated post-commit hook for git-remember
      # This hook captures commit diffs and processes them for memory storage

      git-remember-hook
    """

  logger.info(f"Creating post-commit hook at {hook_path}")
  hook_path.write_text(hook_content)

  # Make it executable
  current_permissions = hook_path.stat().st_mode
  hook_path.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

  logger.info("Post-commit hook created successfully")


def main():
  """Main entry point."""
  parser = argparse.ArgumentParser(
    description="Setup git repository with remember post-commit hook"
  )
  parser.add_argument(
    "repo_path",
    type=Path,
    help="Path to git repository",
  )
  parser.add_argument(
    "--custom",
    action="store_true",
    help="Enable custom handling for specific files (Cache.txt, Scores.csv)",
  )
  args = parser.parse_args()

  repo_path = args.repo_path.resolve()

  # Check if path exists
  if not repo_path.exists():
    logger.error(f"Path does not exist: {repo_path}")
    return 1

  # Check if it's a git repository
  try:
    _repo = Repo(repo_path)
    logger.info(f"Found git repository at {repo_path}")
  except InvalidGitRepositoryError:
    logger.error(f"Not a git repository: {repo_path}")
    return 1

  # Check if post-commit hook already exists
  hook_path = repo_path / ".git" / "hooks" / "post-commit"
  if hook_path.exists():
    logger.error(f"Post-commit hook already exists at {hook_path}")
    logger.error("Remove it first if you want to reinstall")
    return 1

  # Test directory splitting
  try:
    logger.info("Testing directory splitting with LlamaIndex...")
    if args.custom:
      logger.info("Custom file handling enabled")
    nodes = load_and_split_repo(repo_path, enable_custom=args.custom)

    # Print all nodes
    print("\n" + "=" * 80)
    print("NODES FROM DIRECTORY SPLITTING")
    print("=" * 80)
    for i, node in enumerate(nodes, 1):
      print(f"\n--- Node {i}/{len(nodes)} ---")
      print(f"Source: {node.metadata.get('file_path', 'unknown')}")
      print(f"Node metadata:\n{node.metadata}")
      print(f"Node content:\n{node.text}")  # pyright: ignore
      print("-" * 40)

  except Exception as e:
    logger.error(f"Failed to split directory: {e}")
    traceback.print_exc()
    return 1

  # If we got here, splitting succeeded - install the hook
  try:
    create_post_commit_hook(repo_path)
    logger.info("✓ Successfully installed remember post-commit hook")
    logger.info("  The hook will now run after every commit")
    return 0
  except Exception as e:
    logger.error(f"Failed to create post-commit hook: {e}")
    traceback.print_exc()
    return 1


if __name__ == "__main__":
  sys.exit(main())
