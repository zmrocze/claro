#!/usr/bin/env python3
"""Git post-commit hook entry point.

This script is designed to be used as a git post-commit hook.
It parses the diff from the latest commit and prints it in a structured format
that would eventually be sent to Zep memory.
"""

import json
import sys
import traceback

from post_commit_hook import parse_commit_diff


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

    # Print sentence-split nodes
    print("\nSentence-Split Nodes (Added Code):")
    print("=" * 80)
    for node in commit_diff.iter_sentence_nodes():
      filepath = node.metadata.get("filepath", "unknown")
      print(f"\n>>> {filepath}")
      print(node.text)  # pyright: ignore
      print("extra_metadata: ", node.metadata.get("extra_metadata", "nic"))
      # print("extra_metadata: ", node.extra_metadata)  # pyright: ignore
      print("-" * 40)

    return 0

  except Exception as e:
    print(f"Error parsing commit diff: {e}", file=sys.stderr)
    traceback.print_exc()
    return 1


if __name__ == "__main__":
  sys.exit(main())
