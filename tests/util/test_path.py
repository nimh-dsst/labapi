"""Unit tests for NotebookPath class."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from labapi.exceptions import PathError
from labapi.util.path import EscapedSegment, NotebookPath, UnescapedSegment


def test_notebook_path_from_string_absolute():
    """Test NotebookPath creation from an absolute path string."""
    path = NotebookPath(EscapedSegment("/Experiments/2024"))
    assert path.is_absolute() is True
    assert list(path) == ["Experiments", "2024"]
    assert str(path) == "/Experiments/2024"


def test_notebook_path_from_string_relative():
    """Test NotebookPath creation from a relative path string."""
    path = NotebookPath(EscapedSegment("2024/Results"))
    assert path.is_absolute() is False
    assert list(path) == ["2024", "Results"]
    assert str(path) == "2024/Results"


def test_notebook_path_normalization():
    """Test path normalization (dots and empty segments)."""
    path = NotebookPath(EscapedSegment("//Experiments/./2024//Results/../"))
    assert list(path) == ["Experiments", "2024"]
    assert str(path) == "/Experiments/2024"


def test_notebook_path_escaped_slash_is_literal_segment_character():
    """Test escaped slashes do not split path segments."""
    path = NotebookPath(EscapedSegment(r"/Experiments/Figure\/1"))

    assert path.is_absolute() is True
    assert list(path) == ["Experiments", "Figure/1"]
    assert path.name == "Figure/1"
    assert path.to_string() == "/Experiments/Figure/1"
    assert path.to_string(escape=True) == r"/Experiments/Figure\/1"
    assert str(path) == r"/Experiments/Figure\/1"


def test_notebook_path_escaped_segments_with_multiple_parts():
    """Test escaped slashes work across appended path parts."""
    path = NotebookPath(EscapedSegment(r"Folder\/Name"), EscapedSegment(r"Page\/Name"))

    assert path.is_absolute() is False
    assert list(path) == ["Folder/Name", "Page/Name"]


def test_notebook_path_div_operator_accepts_escaped_slashes():
    """Test path appending keeps escaped slashes inside a single segment."""
    path = NotebookPath(EscapedSegment("/Experiments")) / r"Figure\/1"

    assert list(path) == ["Experiments", "Figure/1"]
    assert path.to_string() == "/Experiments/Figure/1"
    assert path.to_string(escape=True) == r"/Experiments/Figure\/1"
    assert str(path) == r"/Experiments/Figure\/1"


def test_notebook_path_escape_unescape_segment():
    """Test escaping and unescaping literal segment values."""
    part = UnescapedSegment("Folder\\Name/Figure")

    escaped = NotebookPath.escape(part)

    assert escaped == (r"Folder\\Name\/Figure",)
    assert NotebookPath.unescape(escaped[0]) == part
    assert NotebookPath.escape(
        UnescapedSegment("Folder/Name"), UnescapedSegment("Page\\Name")
    ) == (
        r"Folder\/Name",
        r"Page\\Name",
    )


@pytest.mark.parametrize(
    ("parts", "escaped"),
    [
        ((), ()),
        (("",), ("",)),
        (("Folder/Name",), (r"Folder\/Name",)),
        (("Folder\\Name",), (r"Folder\\Name",)),
        (
            ("Folder\\Name/Figure", "Page/Name"),
            (r"Folder\\Name\/Figure", r"Page\/Name"),
        ),
    ],
)
def test_notebook_path_escape_returns_tuple_and_round_trips(
    parts: tuple[str, ...], escaped: tuple[str, ...]
):
    """Test escaping multiple parsed segments is stable and reversible."""
    typed_parts = tuple(UnescapedSegment(part) for part in parts)
    typed_escaped = tuple(EscapedSegment(part) for part in escaped)

    assert NotebookPath.escape(*typed_parts) == escaped
    assert tuple(NotebookPath.unescape(part) for part in typed_escaped) == parts


def test_notebook_path_escaped_slash_round_trips_through_string():
    """Test string paths preserve escapes needed to parse them again."""
    path = NotebookPath(EscapedSegment(r"/Experiments/Figure\/1"))

    reparsed = NotebookPath(EscapedSegment(str(path)))

    assert path.to_string() == "/Experiments/Figure/1"
    assert path.to_string(escape=True) == str(path)
    assert reparsed == path
    assert list(reparsed) == ["Experiments", "Figure/1"]


def test_notebook_path_escaped_backslash_round_trips_through_string():
    """Test literal backslashes remain escaped in string paths."""
    path = NotebookPath(EscapedSegment(r"/Folder\\Name/Page\\Name"))

    reparsed = NotebookPath(EscapedSegment(str(path)))

    assert path.to_string() == "/Folder\\Name/Page\\Name"
    assert path.to_string(escape=True) == r"/Folder\\Name/Page\\Name"
    assert str(path) == r"/Folder\\Name/Page\\Name"
    assert reparsed == path
    assert list(reparsed) == ["Folder\\Name", "Page\\Name"]


def test_notebook_path_rejects_trailing_escape_character():
    """Test paths cannot end while escaping the next character."""
    with pytest.raises(PathError, match="Path cannot end with an escape character"):
        NotebookPath(EscapedSegment("Folder\\"))


def test_notebook_path_resolve_preserves_escaped_segments():
    """Test resolving a relative path keeps parsed slash-containing segments."""
    parent = NotebookPath(EscapedSegment(r"/Reports\/2024"))
    path = NotebookPath(EscapedSegment(r"Summary\/Final"), parent=parent)

    resolved = path.resolve()

    assert resolved.is_absolute() is True
    assert list(resolved) == ["Reports/2024", "Summary/Final"]
    assert str(resolved) == r"/Reports\/2024/Summary\/Final"


def test_notebook_path_resolve_parent_argument_preserves_escaped_segments():
    """Test resolving against an explicit parent does not split parsed segments."""
    parent = NotebookPath(EscapedSegment(r"/Reports\/2024"))
    path = NotebookPath(EscapedSegment(r"Summary\/Final"))

    resolved = path.resolve(parent)

    assert resolved.is_absolute() is True
    assert list(resolved) == ["Reports/2024", "Summary/Final"]
    assert str(resolved) == r"/Reports\/2024/Summary\/Final"


def test_notebook_path_resolve_recursive_parent_preserves_escaped_segments():
    """Test recursive parent resolution preserves escaped segments."""
    root = NotebookPath(EscapedSegment(r"/Archive\/Root"))
    parent = NotebookPath(EscapedSegment(r"Reports\/2024"), parent=root)
    path = NotebookPath(EscapedSegment(r"Summary\/Final"))

    resolved = path.resolve(parent, recurse=True)

    assert resolved.is_absolute() is True
    assert list(resolved) == ["Archive/Root", "Reports/2024", "Summary/Final"]
    assert str(resolved) == r"/Archive\/Root/Reports\/2024/Summary\/Final"


def test_notebook_path_relative_to_preserves_escaped_segments():
    """Test relative paths do not split already-parsed slash-containing segments."""
    path = NotebookPath(EscapedSegment(r"/Reports\/2024/Summary\/Final"))
    parent = NotebookPath(EscapedSegment(r"/Reports\/2024"))

    relative = path.relative_to(parent)

    assert relative.is_absolute() is False
    assert list(relative) == ["Summary/Final"]
    assert str(relative) == r"Summary\/Final"
    assert relative.resolve(parent) == path


def test_notebook_path_relative_to_relative_prefix_preserves_escaped_segments():
    """Test relative_to preserves segments when both paths are relative."""
    path = NotebookPath(EscapedSegment(r"Reports\/2024/Summary\/Final"))
    parent = NotebookPath(EscapedSegment(r"Reports\/2024"))

    relative = path.relative_to(parent)

    assert relative.is_absolute() is False
    assert list(relative) == ["Summary/Final"]
    assert str(relative) == r"Summary\/Final"


def test_notebook_path_normalization_with_escaped_slashes():
    """Test parent navigation treats escaped slash segments as one segment."""
    path = NotebookPath(EscapedSegment(r"/Experiments/Figure\/1/../Summary\/Final"))

    assert list(path) == ["Experiments", "Summary/Final"]
    assert str(path) == r"/Experiments/Summary\/Final"


def test_notebook_path_parent_preserves_escaped_segments():
    """Test parent path output keeps literal separator characters escaped."""
    path = NotebookPath(EscapedSegment(r"/Reports\/2024/Summary\/Final"))

    parent = path.parent

    assert list(parent) == ["Reports/2024"]
    assert str(parent) == r"/Reports\/2024"


def test_notebook_path_from_node():
    """Test NotebookPath creation from a tree node."""
    mock_root = Mock()
    mock_root.root = mock_root
    mock_root.name = "Root"

    mock_folder = Mock()
    mock_folder.root = mock_root
    mock_folder.parent = mock_root
    mock_folder.name = "Experiments"

    mock_page = Mock()
    mock_page.root = mock_root
    mock_page.parent = mock_folder
    mock_page.name = "2024"

    path = NotebookPath(mock_page)
    assert path.is_absolute() is True
    assert list(path) == ["Experiments", "2024"]
    assert str(path) == "/Experiments/2024"


def test_notebook_path_from_node_escapes_separator_characters():
    """Test node-derived paths escape literal slash and backslash characters."""
    mock_root = Mock()
    mock_root.root = mock_root
    mock_root.name = "Root"

    mock_folder = Mock()
    mock_folder.root = mock_root
    mock_folder.parent = mock_root
    mock_folder.name = "Reports/2024"

    mock_page = Mock()
    mock_page.root = mock_root
    mock_page.parent = mock_folder
    mock_page.name = "Summary\\Final"

    path = NotebookPath(mock_page)

    assert list(path) == ["Reports/2024", "Summary\\Final"]
    assert str(path) == r"/Reports\/2024/Summary\\Final"


def test_notebook_path_div_operator():
    """Test the / operator for appending segments and paths."""
    base = NotebookPath(EscapedSegment("/Experiments"))
    path = base / "2024" / "Results"

    assert str(path) == "/Experiments/2024/Results"

    # Append relative path
    rel = NotebookPath(EscapedSegment("Sub/Folder"))
    combined = path / rel
    assert str(combined) == "/Experiments/2024/Results/Sub/Folder"

    # Append absolute path returns the absolute path
    abs_path = NotebookPath(EscapedSegment("/Other/Root"))
    result = path / abs_path
    assert str(result) == "/Other/Root"


def test_notebook_path_resolve_relative():
    """Test resolving a relative path against an absolute parent."""
    rel = NotebookPath(EscapedSegment("2024/Results"))
    parent = NotebookPath(EscapedSegment("/Experiments"))

    resolved = rel.resolve(parent)
    assert resolved.is_absolute() is True
    assert str(resolved) == "/Experiments/2024/Results"


def test_notebook_path_resolve_no_parent_raises():
    """Test resolve raises PathError when no parent is available."""
    rel = NotebookPath(EscapedSegment("relative/path"))
    with pytest.raises(
        PathError, match="Cannot resolve relative path without an absolute parent"
    ) as err:
        rel.resolve()
    assert err.value.path == "relative/path"


def test_notebook_path_relative_to_success():
    """Test making a path relative to another."""
    path = NotebookPath(EscapedSegment("/Experiments/2024/Results"))
    base = NotebookPath(EscapedSegment("/Experiments"))

    rel = path.relative_to(base)
    assert rel.is_absolute() is False
    assert str(rel) == "2024/Results"


def test_notebook_path_relative_to_failure():
    """Test relative_to raises PathError if path is outside base."""
    path = NotebookPath(EscapedSegment("/Experiments/2024"))
    other = NotebookPath(EscapedSegment("/Analysis"))

    with pytest.raises(PathError, match="is outside of") as err:
        path.relative_to(other)
    assert err.value.path == "/Experiments/2024"
    assert err.value.parent == "/Analysis"


def test_notebook_path_properties():
    """Test name, parts, and parent properties."""
    path = NotebookPath(EscapedSegment("/Experiments/2024/Results"))

    assert path.name == "Results"
    assert list(path.parts) == ["Experiments", "2024"]
    assert str(path.parent) == "/Experiments/2024"


def test_notebook_path_equality():
    """Test equality and hashing of NotebookPath."""
    p1 = NotebookPath(EscapedSegment("/A/B/C"))
    p2 = NotebookPath(EscapedSegment("/A/B/C"))
    p3 = NotebookPath(EscapedSegment("A/B/C"))

    assert p1 == p2
    assert p1 != p3
    assert hash(p1) == hash(p2)
    assert hash(p1) != hash(p3)


def test_notebook_path_anchored_equals_absolute_with_matching_hash():
    """Anchored and absolute paths that resolve equal must hash equal."""
    anchored = NotebookPath(
        EscapedSegment("b"), parent=NotebookPath(EscapedSegment("/a"))
    )
    absolute = NotebookPath(EscapedSegment("/a/b"))

    assert anchored == absolute
    assert hash(anchored) == hash(absolute)
    assert {anchored: "value"}.get(absolute) == "value"


def test_notebook_path_relative_to_identical_relative_returns_empty():
    """relative_to an identical relative path returns an empty relative path."""
    result = NotebookPath(EscapedSegment("a")).relative_to(
        NotebookPath(EscapedSegment("a"))
    )

    assert result.is_absolute() is False
    assert list(result) == []
    assert str(result) == ""


def test_notebook_path_empty():
    """Test empty path behavior."""
    path = NotebookPath(EscapedSegment(""))
    assert list(path) == []
    assert path.name == "."
    assert str(path) == ""
