#!/usr/bin/env python3
"""Simple test script to verify the git-remember-hook functionality."""

import json
import sys

from remember.diff_parser import parse_commit_diff


def test_parse_commit():
  """Test parsing the latest commit."""
  print("Testing git-remember-hook functionality...")
  print("=" * 80)

  try:
    # Parse the latest commit
    commit_diff = parse_commit_diff("HEAD")

    print(f"✓ Successfully parsed commit: {commit_diff.commit_hash[:8]}")
    print(f"  Author: {commit_diff.author}")
    print(f"  Timestamp: {commit_diff.timestamp}")
    print(f"  Message: {commit_diff.message.split(chr(10))[0]}")

    # Count files (excluding deleted/renamed)
    num_files = sum(
      1 for f in commit_diff.patch_set if not (f.is_removed_file or f.is_rename)
    )
    print(f"  Files changed: {num_files}")

    for file in commit_diff.patch_set:
      if file.is_removed_file or file.is_rename:
        continue
      status = "added" if file.is_added_file else "modified"
      print(f"    - {file.path} ({status})")
      print(f"      +{file.added} -{file.removed}")
      print(f"      Hunks: {len(list(file))}")

    print("\n" + "=" * 80)
    print("JSON output (would be sent to Zep):")
    print("=" * 80)
    print(json.dumps(commit_diff.to_dict(), indent=2))

    print("\n✓ Test passed!")
    return 0

  except Exception as e:
    print(f"✗ Test failed: {e}")
    import traceback

    traceback.print_exc()
    return 1


if __name__ == "__main__":
  sys.exit(test_parse_commit())
