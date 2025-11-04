"""Remember module for git commit tracking and memory submission.

Uses unidiff types (PatchSet, PatchedFile, Hunk, Line) directly.
Only adds commit metadata wrapper via CommitDiff.
"""

from .diff_types import CommitDiff, NewChunk
from .diff_parser import parse_commit_diff

__all__ = [
  "CommitDiff",
  "NewChunk",
  "parse_commit_diff",
]
