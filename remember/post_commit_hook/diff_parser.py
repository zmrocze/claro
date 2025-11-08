"""Parser for git commits using GitPython and unidiff."""

from datetime import datetime
from io import StringIO

from git import Repo
from unidiff import PatchSet

from .diff_types import CommitDiff


def parse_commit_diff(commit_hash: str = "HEAD", repo_path: str = ".") -> CommitDiff:
  """Parse commit diff using GitPython and unidiff.

  Args:
      commit_hash: The commit hash or reference (default: "HEAD")
      repo_path: Path to the git repository (default: current directory)

  Returns:
      CommitDiff with commit metadata and unidiff PatchSet
  """
  # Initialize repository
  repo = Repo(repo_path)
  commit = repo.commit(commit_hash)

  # Get commit metadata
  full_hash = commit.hexsha
  author = f"{commit.author.name} <{commit.author.email}>"
  timestamp = datetime.fromtimestamp(commit.committed_date).isoformat()
  # Ensure message is always a string
  raw_message = commit.message
  message = (
    raw_message.decode("utf-8") if isinstance(raw_message, bytes) else raw_message
  )
  message = message.strip()

  # Get diff from parent (or empty tree if no parent)
  # Use --no-ext-diff to bypass external diff tools (e.g., difftastic)
  # and get standard unified diff format that unidiff can parse
  if commit.parents:
    parent = commit.parents[0]
    diff_text = repo.git.diff(parent.hexsha, commit.hexsha, unified=3, no_ext_diff=True)
  else:
    # Initial commit - diff against empty tree
    diff_text = repo.git.show(commit.hexsha, format="", unified=3, no_ext_diff=True)

  print(f"Diff text: {diff_text}")

  # Parse diff using unidiff - use their types directly!
  patch_set = PatchSet(StringIO(diff_text))

  return CommitDiff(
    commit_hash=full_hash,
    author=author,
    timestamp=timestamp,
    message=message,
    patch_set=patch_set,
  )
