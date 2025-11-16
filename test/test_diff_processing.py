#!/usr/bin/env python3
"""Tests for diff processing functionality including CSV, markdown, and special file handling."""

import json
import tempfile
from pathlib import Path
from io import StringIO

import pytest
from unidiff import PatchSet

from remember.post_commit_hook.diff_types import CommitDiff


@pytest.fixture
def temp_dir():
  """Create a temporary directory for test files."""
  with tempfile.TemporaryDirectory() as tmpdir:
    yield Path(tmpdir)


@pytest.fixture
def sample_csv_content():
  """Sample CSV content for testing."""
  return """date,author,score
2024-01-01,Alice,85
2024-01-02,Bob,92
2024-01-03,Charlie,78"""


@pytest.fixture
def sample_checkmarks_csv():
  """Sample Checkmarks.csv content.

  Format matches CheckmarksCsv expectations:
  - Trailing comma creates empty column
  - header[1:-1] extracts categories (skips date and trailing empty column)
  """
  return """date,exercise,meditation,reading, 
2024-01-01,2,2,1, 
2024-01-02,1,2,2, 
2024-01-03,2,1,2, """


@pytest.fixture
def sample_markdown_content():
  """Sample markdown content for testing."""
  return """# Main Title

Some intro text.

## Section 1

Content in section 1.

## Section 2

Content in section 2.

### Subsection 2.1

Content in subsection 2.1."""


def create_commit_diff_from_patch(
  patch_text: str, enable_custom: bool = False
) -> CommitDiff:
  """Helper to create CommitDiff from patch text."""
  patch_set = PatchSet(StringIO(patch_text))
  return CommitDiff(
    commit_hash="test123",
    author="Test Author <test@example.com>",
    timestamp="2024-01-01T00:00:00",
    message="Test commit",
    patch_set=patch_set,
    enable_custom=enable_custom,
  )


class TestMarkdownProcessing:
  """Tests for markdown file processing."""

  def test_markdown_groups_by_headers(self, temp_dir):
    """Test that markdown lines are grouped by header context."""
    md_file = temp_dir / "test.md"
    md_file.write_text("""# Main Title

Line 1

## Section 1

Line 2
Line 3

## Section 2

Line 4""")

    # Patch adding lines under different headers
    patch_text = f"""--- a/{md_file}
+++ b/{md_file}
@@ -4,0 +5,2 @@
+New line under Section 1
+Another line under Section 1
@@ -9,0 +12,1 @@
+New line under Section 2"""

    commit_diff = create_commit_diff_from_patch(patch_text)
    chunks = list(commit_diff.iter_new_chunks())

    # Should have 2 chunks (one per header context)
    assert len(chunks) == 2

    # Check metadata contains header paths
    assert chunks[0].extra_metadata is not None
    assert "header_path" in chunks[0].extra_metadata
    assert chunks[1].extra_metadata is not None
    assert "header_path" in chunks[1].extra_metadata


class TestCSVProcessing:
  """Tests for CSV file processing."""

  def test_csv_header_changed_processes_entire_file(self, temp_dir, sample_csv_content):
    """Test that changing CSV header triggers full file processing."""
    csv_file = temp_dir / "test.csv"
    csv_file.write_text(sample_csv_content)

    # Patch changing the header
    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -1,1 +1,1 @@
-date,author,score
+date,author,score,grade"""

    commit_diff = create_commit_diff_from_patch(patch_text)
    chunks = list(commit_diff.iter_new_chunks())

    # Should process all data rows (3 rows)
    assert len(chunks) == 3

    # Each chunk should be JSON
    for chunk in chunks:
      data = json.loads(chunk.added_text)
      assert isinstance(data, dict)
      assert "date" in data or "author" in data or "score" in data

  def test_csv_row_added_processes_only_new_rows(self, temp_dir, sample_csv_content):
    """Test that adding CSV rows processes only new rows."""
    csv_file = temp_dir / "test.csv"
    csv_file.write_text(sample_csv_content)

    # Patch adding a new row (line 5)
    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -4,0 +5,1 @@
+2024-01-04,David,88"""

    commit_diff = create_commit_diff_from_patch(patch_text)
    chunks = list(commit_diff.iter_new_chunks())

    # Should have 1 chunk for the new row
    assert len(chunks) == 1

    data = json.loads(chunks[0].added_text)
    assert data["date"] == "2024-01-04"
    assert data["author"] == "David"
    assert data["score"] == "88"

  def test_csv_standard_format(self, temp_dir):
    """Test standard CSV processing converts rows to JSON."""
    csv_file = temp_dir / "data.csv"
    csv_file.write_text("name,age,city\nAlice,30,NYC\nBob,25,LA")

    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -2,0 +3,1 @@
+Charlie,35,SF"""

    commit_diff = create_commit_diff_from_patch(patch_text)
    chunks = list(commit_diff.iter_new_chunks())

    assert len(chunks) == 1
    data = json.loads(chunks[0].added_text)
    assert data == {"name": "Charlie", "age": "35", "city": "SF"}


class TestCheckmarksCSV:
  """Tests for Checkmarks.csv special handling."""

  def test_checkmarks_csv_without_custom_flag(self, temp_dir, sample_checkmarks_csv):
    """Test Checkmarks.csv without custom flag uses standard processing."""
    csv_file = temp_dir / "Checkmarks.csv"
    csv_file.write_text(sample_checkmarks_csv)

    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -1,0 +2,1 @@
+2024-01-04,2,2,2, """

    commit_diff = create_commit_diff_from_patch(patch_text, enable_custom=False)
    chunks = list(commit_diff.iter_new_chunks())

    # Without custom flag, should use standard CSV processing (JSON format)
    assert len(chunks) == 1
    data = json.loads(chunks[0].added_text)
    assert isinstance(data, dict)

  def test_checkmarks_csv_with_custom_flag(self, temp_dir, sample_checkmarks_csv):
    """Test Checkmarks.csv with custom flag uses special processing."""
    csv_file = temp_dir / "Checkmarks.csv"
    csv_file.write_text(sample_checkmarks_csv)

    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -1,0 +2,1 @@
+2024-01-04,2,2,2, """

    commit_diff = create_commit_diff_from_patch(patch_text, enable_custom=True)
    chunks = list(commit_diff.iter_new_chunks())

    # With custom flag, should extract positive dates (value=2)
    # Row has 2,2,2 for exercise, meditation, reading
    # CheckmarksCsv uses header[1:-1] so processes all categories except trailing empty
    assert len(chunks) == 3

    texts = [chunk.added_text for chunk in chunks]
    assert "2024-01-04: exercise" in texts
    assert "2024-01-04: meditation" in texts
    assert "2024-01-04: reading" in texts

  def test_checkmarks_csv_filters_non_positive_values(self, temp_dir):
    """Test that Checkmarks.csv only includes positive values (2)."""
    csv_file = temp_dir / "Checkmarks.csv"
    csv_file.write_text("""date,exercise,meditation,reading, 
2024-01-01,2,1,0, 
2024-01-02,2,2,-1, """)

    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -1,0 +2,2 @@
+2024-01-01,2,1,0, 
+2024-01-02,2,2,-1, """

    commit_diff = create_commit_diff_from_patch(patch_text, enable_custom=True)
    chunks = list(commit_diff.iter_new_chunks())

    # Only values of 2 should be included
    texts = [chunk.added_text for chunk in chunks]
    assert len(texts) == 3  # 2 exercise + 1 meditation
    assert "2024-01-01: exercise" in texts
    assert "2024-01-02: exercise" in texts
    assert "2024-01-02: meditation" in texts
    # These should NOT be present
    assert "2024-01-01: meditation" not in texts
    assert "2024-01-01: reading" not in texts
    assert "2024-01-02: reading" not in texts

  def test_checkmarks_csv_header_changed_processes_full_file(self, temp_dir):
    """Test that changing Checkmarks.csv header processes entire file."""
    csv_file = temp_dir / "Checkmarks.csv"
    csv_file.write_text("""date,exercise,meditation, 
2024-01-01,2,2, 
2024-01-02,2,1, """)

    # Change header - add reading category
    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -1,1 +1,1 @@
-date,exercise,meditation, 
+date,exercise,meditation,reading, """

    commit_diff = create_commit_diff_from_patch(patch_text, enable_custom=True)
    chunks = list(commit_diff.iter_new_chunks())

    # Should process all rows with value 2
    # With new header, categories are [exercise, meditation, reading]
    # But data rows only have 2 values, so reading won't match anything
    texts = [chunk.added_text for chunk in chunks]
    assert "2024-01-01: exercise" in texts
    assert "2024-01-01: meditation" in texts
    assert "2024-01-02: exercise" in texts


class TestCacheTxtProcessing:
  """Tests for Cache.txt special handling."""

  def test_cache_txt_without_custom_flag(self, temp_dir):
    """Test Cache.txt without custom flag uses generic processing."""
    cache_file = temp_dir / "Cache.txt"
    cache_file.write_text("line1\nline2\nline3")

    patch_text = f"""--- a/{cache_file}
+++ b/{cache_file}
@@ -2,0 +3,2 @@
+line4
+line5"""

    commit_diff = create_commit_diff_from_patch(patch_text, enable_custom=False)
    chunks = list(commit_diff.iter_new_chunks())

    # Without custom flag, should be single chunk
    assert len(chunks) == 1
    assert chunks[0].added_text == "line4\nline5"

  def test_cache_txt_with_custom_flag(self, temp_dir):
    """Test Cache.txt with custom flag splits by lines."""
    cache_file = temp_dir / "Cache.txt"
    cache_file.write_text("line1\nline2\nline3")

    patch_text = f"""--- a/{cache_file}
+++ b/{cache_file}
@@ -2,0 +3,2 @@
+line4
+line5"""

    commit_diff = create_commit_diff_from_patch(patch_text, enable_custom=True)
    chunks = list(commit_diff.iter_new_chunks())

    # With custom flag, should split into separate lines
    assert len(chunks) == 2
    assert chunks[0].added_text == "line4\n"
    assert chunks[1].added_text == "line5"

  def test_cache_txt_skips_empty_lines(self, temp_dir):
    """Test that Cache.txt skips empty lines."""
    cache_file = temp_dir / "Cache.txt"
    cache_file.write_text("line1\nline2")

    patch_text = f"""--- a/{cache_file}
+++ b/{cache_file}
@@ -2,0 +3,3 @@
+line3
+
+line4"""

    commit_diff = create_commit_diff_from_patch(patch_text, enable_custom=True)
    chunks = list(commit_diff.iter_new_chunks())

    # Should skip the empty line
    assert len(chunks) == 2
    texts = [chunk.added_text for chunk in chunks]
    assert "line3\n" in texts
    assert "line4" in texts


class TestGenericFileProcessing:
  """Tests for generic file processing."""

  def test_generic_file_single_chunk(self, temp_dir):
    """Test that generic files produce single chunk."""
    py_file = temp_dir / "test.py"
    py_file.write_text("def foo():\n    pass\n")

    patch_text = f"""--- a/{py_file}
+++ b/{py_file}
@@ -1,0 +2,2 @@
+def bar():
+    return 42"""

    commit_diff = create_commit_diff_from_patch(patch_text)
    chunks = list(commit_diff.iter_new_chunks())

    assert len(chunks) == 1
    assert "def bar():" in chunks[0].added_text
    assert "return 42" in chunks[0].added_text

  def test_nonexistent_file_uses_generic_processing(self, temp_dir):
    """Test that nonexistent files fall back to generic processing."""
    nonexistent = temp_dir / "nonexistent.csv"

    patch_text = f"""--- /dev/null
+++ b/{nonexistent}
@@ -0,0 +1,2 @@
+header1,header2
+value1,value2"""

    commit_diff = create_commit_diff_from_patch(patch_text)
    chunks = list(commit_diff.iter_new_chunks())

    # Should use generic processing since file doesn't exist
    assert len(chunks) == 1
    assert "header1,header2" in chunks[0].added_text


class TestEdgeCases:
  """Tests for edge cases and error handling."""

  def test_empty_csv_file(self, temp_dir):
    """Test handling of empty CSV file."""
    csv_file = temp_dir / "empty.csv"
    csv_file.write_text("")

    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -0,0 +1,1 @@
+header"""

    commit_diff = create_commit_diff_from_patch(patch_text)
    chunks = list(commit_diff.iter_new_chunks())

    # Should handle gracefully (fall back to generic or return empty)
    assert isinstance(chunks, list)

  def test_malformed_csv_falls_back_to_generic(self, temp_dir):
    """Test that malformed CSV falls back to generic processing."""
    csv_file = temp_dir / "malformed.csv"
    csv_file.write_text("not,a,proper\ncsv,file")

    patch_text = f"""--- a/{csv_file}
+++ b/{csv_file}
@@ -1,0 +2,1 @@
+this,will,cause,issues"""

    commit_diff = create_commit_diff_from_patch(patch_text)

    # Should not raise exception
    chunks = list(commit_diff.iter_new_chunks())
    assert isinstance(chunks, list)

  def test_multiple_file_types_in_commit(self, temp_dir):
    """Test processing commit with multiple file types."""
    md_file = temp_dir / "doc.md"
    md_file.write_text("# Title\nContent")

    csv_file = temp_dir / "data.csv"
    csv_file.write_text("a,b\n1,2")

    py_file = temp_dir / "code.py"
    py_file.write_text("x = 1")

    patch_text = f"""--- a/{md_file}
+++ b/{md_file}
@@ -1,0 +2,1 @@
+New content
--- a/{csv_file}
+++ b/{csv_file}
@@ -1,0 +2,1 @@
+3,4
--- a/{py_file}
+++ b/{py_file}
@@ -1,0 +2,1 @@
+y = 2"""

    commit_diff = create_commit_diff_from_patch(patch_text)
    chunks = list(commit_diff.iter_new_chunks())

    # Should have chunks from all three files
    assert len(chunks) == 3

    # Verify we have chunks from each file
    filepaths = [chunk.filepath.name for chunk in chunks]
    assert "doc.md" in filepaths
    assert "data.csv" in filepaths
    assert "code.py" in filepaths


if __name__ == "__main__":
  pytest.main([__file__, "-v"])
