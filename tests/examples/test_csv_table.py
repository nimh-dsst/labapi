"""Tests for the csv_table example script."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import Mock

import pytest

from labapi import TextEntry, User


def load_csv_table_module():
    """Load a CSV table example module for direct unit testing."""
    script_dir = Path(__file__).resolve().parents[2] / "examples" / "csv_table"
    script_path = script_dir / "csv_table.py"
    module_name = "csv_table_example"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(module_name)
    previous_path = list(sys.path)
    sys.modules[module_name] = module
    sys.path.insert(0, str(script_dir))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous_path
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module

    return module


csv_table = load_csv_table_module()


class _DirectoryNode:
    def as_page(self):
        raise TypeError("Node is not a page")


class _NotebookDouble:
    def __init__(self, node: object):
        self.node = node

    def traverse(self, _path: str):
        return self.node

    def page(self, _path: str):
        return self.node


class _UserDouble:
    def __init__(self, notebook):
        self.notebooks = {"My Notebook": notebook}


class _EntriesDouble(list):
    def __init__(self, entries: Iterable[object] = ()):
        super().__init__(entries)
        self.created: list[tuple[type[TextEntry], str]] = []

    def create(self, cls: type[TextEntry], data: str):
        self.created.append((cls, data))
        return SimpleNamespace(id="entry-123")


class _PageNode:
    def __init__(self, entries: Iterable[object] = ()):
        self.entries = _EntriesDouble(entries)

    def as_page(self):
        return self


def _text_entry(content: str, entry_id: str = "entry-id") -> TextEntry:
    return TextEntry(entry_id, content, cast(User, Mock(spec=User)))


def test_upload_table_returns_result_without_cli_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """Test the reusable upload function lets callers own CLI output."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("Name,Value\nA&B,<ok>\n", encoding="utf-8")
    page = _PageNode()
    user = _UserDouble(_NotebookDouble(page))

    result = csv_table.upload_table(
        user,
        csv_table.UploadTableOptions(
            notebook_name="My Notebook",
            csv_file=csv_file,
            page_path="Results/Page",
        ),
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert result.entry_id == "entry-123"
    assert result.row_count == 1
    assert result.column_count == 2
    assert page.entries.created[0][0] is TextEntry
    html = page.entries.created[0][1]
    assert "<table>" in html
    assert "<th>Name</th>" in html
    assert "<td>A&amp;B</td>" in html
    assert "<td>&lt;ok&gt;</td>" in html


def test_upload_table_can_treat_first_csv_row_as_data(tmp_path: Path):
    """Test upload can render every CSV row as table data."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("alpha,1\nbeta,2\n", encoding="utf-8")
    page = _PageNode()
    user = _UserDouble(_NotebookDouble(page))

    result = csv_table.upload_table(
        user,
        csv_table.UploadTableOptions(
            notebook_name="My Notebook",
            csv_file=csv_file,
            page_path="Results/Page",
            has_header=False,
        ),
    )

    html = page.entries.created[0][1]
    assert result.row_count == 2
    assert result.column_count == 2
    assert "<thead>" not in html
    assert "<td>alpha</td>" in html
    assert "<td>beta</td>" in html


def test_download_table_writes_most_recent_html_table(tmp_path: Path):
    """Test download writes the most recent table entry back to CSV."""
    output_file = tmp_path / "table.csv"
    page = _PageNode(
        [
            _text_entry("<p>No table here</p>", "entry-1"),
            _text_entry(
                """
                <table>
                  <tbody><tr><td>old</td><td>1</td></tr></tbody>
                </table>
                """,
                "entry-2",
            ),
            _text_entry(
                """
                <table>
                  <thead><tr><th>Name</th><th>Value</th></tr></thead>
                  <tbody><tr><td>A&amp;B</td><td>&lt;ok&gt;</td></tr></tbody>
                </table>
                """,
                "entry-3",
            ),
        ]
    )
    user = _UserDouble(_NotebookDouble(page))

    result = csv_table.download_table(
        user,
        csv_table.DownloadTableOptions(
            notebook_name="My Notebook",
            page_path="Results/Page",
            output_file=output_file,
        ),
    )

    assert result.entry_index == 2
    assert result.row_count == 1
    assert result.column_count == 2
    assert output_file.read_text(encoding="utf-8") == "Name,Value\nA&B,<ok>\n"


def test_download_table_can_use_explicit_entry_index(tmp_path: Path):
    """Test download can select a specific table entry."""
    output_file = tmp_path / "table.csv"
    page = _PageNode(
        [
            _text_entry(
                "<table><tbody><tr><td>first</td><td>1</td></tr></tbody></table>"
            ),
            _text_entry(
                "<table><tbody><tr><td>second</td><td>2</td></tr></tbody></table>"
            ),
        ]
    )
    user = _UserDouble(_NotebookDouble(page))

    result = csv_table.download_table(
        user,
        csv_table.DownloadTableOptions(
            notebook_name="My Notebook",
            page_path="Results/Page",
            output_file=output_file,
            entry_index=0,
        ),
    )

    assert result.entry_index == 0
    assert output_file.read_text(encoding="utf-8") == "first,1\n"


def test_download_table_raises_on_directory_path(
    capsys: pytest.CaptureFixture[str],
):
    """Test the reusable download function reports a directory path as an error."""
    notebook = _NotebookDouble(_DirectoryNode())
    user = _UserDouble(notebook)

    with pytest.raises(TypeError, match="Node is not a page"):
        csv_table.download_table(
            user,
            csv_table.DownloadTableOptions(
                notebook_name="My Notebook",
                page_path="Results",
                output_file=Path("table-output.csv"),
            ),
        )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_cli_parser_defaults_to_recent_table_entry():
    """Test the CLI keeps the table download default."""
    args = csv_table._build_parser().parse_args(
        ["download", "Results/Page", "output.csv", "--notebook", "My Notebook"]
    )

    assert args.entry_index == -1
