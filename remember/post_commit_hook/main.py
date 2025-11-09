#!/usr/bin/env python3
"""Git post-commit hook entry point.

This script is designed to be used as a git post-commit hook.
It parses the diff from the latest commit and prints it in a structured format
that would eventually be sent to Zep memory.
"""

import json
import logging
import sys
import traceback
import argparse

from post_commit_hook import parse_commit_diff
from remember.send import ZepConfig, print_action, zep_action

logger = logging.getLogger(__name__)

# Command line argument parser
parser = argparse.ArgumentParser(
  description="Git post-commit hook with Zep integration"
)
parser.add_argument("--api-key", help="Zep API key")
parser.add_argument("--user-id", help="Zep user ID")
parser.add_argument(
  "--only-print", action="store_true", help="Only print nodes without sending to Zep"
)


def main():
  """Parse and print the structured diff from the latest commit."""
  try:
    # Parse the commit diff (default repo_path="." will work from git repo)
    commit_diff = parse_commit_diff("HEAD")

    # Convert to dict for JSON serialization
    diff_dict = commit_diff.to_dict()

    # Print formatted JSON
    print("=" * 80)
    print("GIT COMMIT DIFF - Would be sent to Zep Memory")
    print("=" * 80)
    print(json.dumps(diff_dict, indent=2))
    print("=" * 80)

    # Print summary
    print("\nSummary:")
    print(f"  Commit: {commit_diff.commit_hash[:8]}")
    print(f"  Author: {commit_diff.author}")
    # Get first line of commit message
    first_line = commit_diff.message.split("\n")[0]
    print(f"  Message: {first_line}")
    print(f"commit_diff.patch_set: {commit_diff.patch_set}")
    print(f"commit_diff.patch_set: {type(commit_diff.patch_set)}")
    # Count files (excluding deleted/renamed)
    num_files = sum(
      1 for f in commit_diff.patch_set if not (f.is_removed_file or f.is_rename)
    )
    print(f"  Files changed: {num_files}")

    for file in commit_diff.patch_set:
      if file.is_removed_file or file.is_rename:
        continue
      status = "added" if file.is_added_file else "modified"
      print(f"    - {file.path} ({status}): +{file.added} -{file.removed}")

    nodes = list(commit_diff.iter_sentence_nodes())

    print(f"  Nodes: {len(nodes)}")

    if len(nodes) > 0:
      args, _ = parser.parse_known_args()
      if args.only_print:
        print_action(nodes)
      else:
        zep_config = ZepConfig.get_zep_config(args, logger)
        zep_action(nodes, zep_config, print)

    return 0

  except Exception as e:
    logger.error(f"Error parsing commit diff and submitting to zep: {e}")
    traceback.print_exc()
    return 1


if __name__ == "__main__":
  sys.exit(main())
