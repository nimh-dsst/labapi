"""Tests for the folder_download example script."""

from __future__ import annotations

import importlib.util
import sys
from io import BytesIO
from pathlib import Path
from types import TracebackType
from typing import cast

import pytest

from labapi import (
    Attachment,
    AttachmentEntry,
    HeaderEntry,
    PlainTextEntry,
    TextEntry,
    UnknownEntry,
    User,
    WidgetEntry,
)


def load_folder_download_module():
    """Load the example script as a module for direct unit testing."""
    script_path = (
        Path(__file__).resolve().parents[2]
        / "examples"
        / "folder_download"
        / "folder_download.py"
    )
    module_name = "folder_download_example"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    previous_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        if previous_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous_module
    return module


folder_download = load_folder_download_module()


class _PageDouble:
    """Minimal page double exposing entries."""

    def __init__(
        self,
        name: str,
        page_id: str,
        entries: list[object] | None = None,
    ):
        """Initialize the page metadata and entries."""
        self.name = name
        self.id = page_id
        self.entries = entries or []

    def is_dir(self) -> bool:
        """Return false because this node is a page."""
        return False

    def as_page(self) -> _PageDouble:
        """Return this page."""
        return self


class _DirectoryDouble:
    """Minimal directory/notebook double exposing children."""

    def __init__(
        self,
        name: str,
        directory_id: str,
        children: list[object] | None = None,
        traverse_result: object | None = None,
    ):
        """Initialize the directory metadata and traversal behavior."""
        self.name = name
        self.id = directory_id
        self.children = children or []
        self.traverse_result = traverse_result
        self.traverse_calls: list[str] = []

    def is_dir(self) -> bool:
        """Return true because this node is a directory."""
        return True

    def as_dir(self) -> _DirectoryDouble:
        """Return this directory."""
        return self

    def traverse(self, path: str) -> object:
        """Record traversal and return the configured node."""
        self.traverse_calls.append(path)
        assert self.traverse_result is not None
        return self.traverse_result


class _UserDouble:
    """Minimal user double exposing the notebooks mapping."""

    def __init__(self, notebook: _DirectoryDouble):
        """Initialize the user double with one notebook."""
        self.notebooks = {"My Notebook": notebook}


class _ClientDouble:
    """Minimal client context manager double."""

    def __init__(self, user: _UserDouble):
        """Initialize the client double with an authenticated user."""
        self._user = user

    def __enter__(self) -> _ClientDouble:
        """Return this client double."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Exit the client context manager."""
        del exc_type, exc, traceback

    def default_authenticate(self) -> _UserDouble:
        """Return the configured authenticated user."""
        return self._user


def _user() -> User:
    """Return a typed user placeholder for entry doubles."""
    return cast(User, object())


def _attachment_entry(
    entry_id: str,
    payload: bytes,
    *,
    filename: str = "data.csv",
    caption: str = "",
) -> AttachmentEntry:
    """Create an attachment entry double with in-memory content."""
    entry = AttachmentEntry(entry_id, caption, _user())

    def get_attachment(use_tempfile: bool = False) -> Attachment:
        del use_tempfile
        return Attachment(
            BytesIO(payload),
            "application/octet-stream",
            filename,
            caption,
        )

    entry.get_attachment = get_attachment
    return entry


def _failing_attachment_entry(entry_id: str) -> AttachmentEntry:
    """Create an attachment entry double that fails during content retrieval."""
    entry = AttachmentEntry(entry_id, "caption", _user())

    def get_attachment(use_tempfile: bool = False) -> Attachment:
        del use_tempfile
        raise RuntimeError("content unavailable")

    entry.get_attachment = get_attachment
    return entry


def test_cli_module_import_has_no_side_effects():
    """Test importing the CLI module does not run authentication."""
    parser = folder_download._build_parser()

    args = parser.parse_args(["./backup", "--notebook", "My Notebook"])

    assert args.output == "./backup"
    assert args.notebook == "My Notebook"


def test_get_unique_path_returns_sanitized_name(tmp_path: Path):
    """Test unique paths preserve the original sanitized name when unused."""
    used_paths: set[Path] = set()

    path = folder_download.get_unique_path(
        tmp_path,
        "Experiment:1",
        used_paths,
        "page-one",
    )

    assert path == tmp_path / "Experiment_1"
    assert path in used_paths


def test_get_unique_path_uses_id_suffix_on_collision(tmp_path: Path):
    """Test colliding sanitized names are disambiguated with the node id."""
    used_paths: set[Path] = set()

    first = folder_download.get_unique_path(
        tmp_path,
        "Experiment:1",
        used_paths,
        "page-one",
    )
    second = folder_download.get_unique_path(
        tmp_path,
        "Experiment/1",
        used_paths,
        "page-two",
    )

    assert first == tmp_path / "Experiment_1"
    assert second == tmp_path / "Experiment_1_page-two"


def test_download_page_writes_supported_entries_without_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    """Test page download writes files and keeps reusable output quiet."""
    page = _PageDouble(
        "Experiment:1",
        "page-one",
        [
            HeaderEntry("entry-1", "Summary", _user()),
            TextEntry("entry-2", "<p>Results</p>", _user()),
            PlainTextEntry("entry-3", "notes", _user()),
            _attachment_entry(
                "entry-4",
                b"sample,data\n",
                filename="../data.csv",
                caption="Data caption",
            ),
            WidgetEntry("entry-5", "ignored", _user()),
            UnknownEntry("entry-6", "payload", _user(), part_type="future entry"),
        ],
    )

    result = folder_download._download_page(page, tmp_path, set())

    captured = capsys.readouterr()
    page_dir = tmp_path / "Experiment_1"
    assert captured.out == ""
    assert captured.err == ""
    assert result.page_count == 1
    assert result.entry_count == 6
    assert result.error_count == 0
    assert (page_dir / "_metadata.txt").read_text(encoding="utf-8") == (
        "Page: Experiment:1\nID: page-one\nEntry count: 6\n"
    )
    assert (page_dir / "001_header.txt").read_text(encoding="utf-8") == "Summary"
    assert (page_dir / "002_text.html").read_text(encoding="utf-8") == "<p>Results</p>"
    assert (page_dir / "003_plaintext.txt").read_text(encoding="utf-8") == "notes"
    assert (page_dir / "004_attachment_data.csv").read_bytes() == b"sample,data\n"
    assert (page_dir / "004_caption.txt").read_text(encoding="utf-8") == "Data caption"
    assert "Widget Entry" in (page_dir / "005_widget.txt").read_text(encoding="utf-8")
    assert "future entry" in (page_dir / "006_unknown.txt").read_text(encoding="utf-8")


def test_download_page_uses_collision_safe_directory_names(tmp_path: Path):
    """Test page downloads do not merge different names into one directory."""
    used_paths: set[Path] = set()

    folder_download._download_page(
        _PageDouble("Experiment:1", "page-one"), tmp_path, used_paths
    )
    folder_download._download_page(
        _PageDouble("Experiment/1", "page-two"), tmp_path, used_paths
    )

    assert (tmp_path / "Experiment_1").is_dir()
    assert (tmp_path / "Experiment_1_page-two").is_dir()


def test_download_page_records_entry_errors(tmp_path: Path):
    """Test failed entries are captured in the result and error file."""
    page = _PageDouble(
        "Experiment",
        "page-one",
        [_failing_attachment_entry("entry-error")],
    )

    result = folder_download._download_page(page, tmp_path, set())

    error_file = tmp_path / "Experiment" / "001_error.txt"
    assert result.entry_count == 1
    assert result.error_count == 1
    assert result.errors[0].entry_id == "entry-error"
    assert result.errors[0].error_file == error_file
    assert "content unavailable" in error_file.read_text(encoding="utf-8")


def test_download_notebook_or_folder_returns_structured_summary(tmp_path: Path):
    """Test reusable notebook download traverses and summarizes a subtree."""
    page = _PageDouble(
        "Results",
        "page-one",
        [PlainTextEntry("entry-1", "value", _user())],
    )
    directory = _DirectoryDouble("Experiments", "dir-one", [page])
    notebook = _DirectoryDouble(
        "My Notebook", "notebook-one", traverse_result=directory
    )
    user = _UserDouble(notebook)

    result = folder_download.download_notebook_or_folder(
        user,
        folder_download.DownloadFolderOptions(
            notebook_name="My Notebook",
            output_dir=tmp_path,
            path="Experiments",
        ),
    )

    assert notebook.traverse_calls == ["Experiments"]
    assert result.directory_count == 1
    assert result.page_count == 1
    assert result.entry_count == 1
    assert (tmp_path / "Experiments" / "Results" / "001_plaintext.txt").read_text(
        encoding="utf-8"
    ) == "value"


def test_main_reports_summary_and_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    """Test the CLI owns output and process exit codes."""
    output_dir = tmp_path / "export"
    page = _PageDouble(
        "Results",
        "page-one",
        [_failing_attachment_entry("entry-error")],
    )
    notebook = _DirectoryDouble("My Notebook", "notebook-one", [page])
    user = _UserDouble(notebook)
    monkeypatch.setattr(folder_download, "Client", lambda: _ClientDouble(user))

    exit_code = folder_download.main([str(output_dir), "--notebook", "My Notebook"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Downloaded 1 directories, 1 pages, and 1 entries" in captured.out
    assert "1 entries could not be fully exported" in captured.out
