"""Tests for the json_sync example script."""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Iterator, Sequence
from io import BytesIO
from pathlib import Path
from types import TracebackType
from typing import cast

import pytest
from typing_extensions import Self

from labapi import (
    Attachment,
    AttachmentEntry,
    JsonData,
    TraversalError,
    User,
)

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "json_sync"


def _load_example_module(module_name: str, filename: str):
    """Load an example module from the json_sync example directory."""
    module_path = EXAMPLE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(EXAMPLE_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


json_sync = _load_example_module("json_sync", "json_sync.py")


class _RecordingEntries:
    """Minimal entries collection double."""

    def __init__(self, entries: Sequence[AttachmentEntry] = ()):
        """Initialize the entries collection double."""
        self._entries = list(entries)
        self.created_json: list[tuple[JsonData, str | None, str | None]] = []

    def __iter__(self) -> Iterator[AttachmentEntry]:
        """Iterate over configured entries."""
        return iter(self._entries)

    def create_json_entry(
        self,
        data: JsonData,
        *,
        filename: str | None = None,
        caption: str | None = None,
    ) -> None:
        """Record JSON entry creation and return fake entry IDs."""
        self.created_json.append((data, filename, caption))


class _PageDouble:
    """Minimal page double exposing entries."""

    def __init__(self, entries: _RecordingEntries):
        """Initialize the page double."""
        self.entries = entries


class _PageNode:
    """Minimal tree node that resolves to a page."""

    def __init__(self, page: _PageDouble):
        """Initialize the page node."""
        self._page = page

    def is_dir(self) -> bool:
        """Return false because this node is a page."""
        return False

    def as_page(self) -> _PageDouble:
        """Return the configured page."""
        return self._page


class _RecordingContainer:
    """Minimal container double for page traversal and creation tests."""

    def __init__(
        self,
        traverse_result: _PageNode | None = None,
        traverse_error: Exception | None = None,
    ):
        """Initialize the container double with traversal behavior."""
        self.traverse_result = traverse_result
        self.traverse_error = traverse_error
        self.page_calls: list[str] = []

    def traverse(self, _path: str) -> _PageNode:
        """Return the configured traversal result or raise the configured error."""
        if self.traverse_error is not None:
            raise self.traverse_error
        assert self.traverse_result is not None
        return self.traverse_result

    def page(self, path: str) -> _PageDouble:
        """Record a page request and return the configured page."""
        self.page_calls.append(path)
        assert self.traverse_result is not None
        return self.traverse_result.as_page()


class _UserDouble:
    """Minimal user double exposing the notebooks mapping."""

    def __init__(self, notebook: _RecordingContainer):
        """Initialize the user double with one notebook."""
        self.notebooks = {"My Notebook": notebook}


class _ClientDouble:
    """Minimal client context manager double."""

    def __init__(self, user: _UserDouble):
        """Initialize the client double with an authenticated user."""
        self._user = user

    def __enter__(self) -> Self:
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


def _make_attachment_entry(
    entry_id: str,
    filename: str,
    mime_type: str,
    payload: bytes,
) -> AttachmentEntry:
    """Create an attachment entry double with in-memory content."""
    entry = AttachmentEntry(entry_id, "caption", cast(User, object()))

    def get_attachment(use_tempfile: bool = False) -> Attachment:
        del use_tempfile
        return Attachment(
            BytesIO(payload),
            mime_type,
            filename,
            "caption",
        )

    entry.get_attachment = get_attachment
    return entry


def _make_failing_attachment_entry(entry_id: str) -> AttachmentEntry:
    """Create an attachment entry whose content retrieval raises."""
    entry = AttachmentEntry(entry_id, "caption", cast(User, object()))

    def get_attachment(use_tempfile: bool = False) -> Attachment:
        del use_tempfile
        raise RuntimeError("content unavailable")

    entry.get_attachment = get_attachment
    return entry


def test_cli_module_import_has_no_side_effects():
    """Test importing the CLI module does not run authentication."""
    parser = json_sync.build_parser()

    args = parser.parse_args(
        ["upload", "sample_data", "Data/Page", "--notebook", "My Notebook"]
    )

    assert args.action == "upload"
    assert args.notebook == "My Notebook"


def test_download_json_files_raises_on_traversal_error():
    """Test the reusable download helper raises instead of exiting."""
    notebook = _RecordingContainer(
        traverse_error=TraversalError(
            "missing child",
            path="/Missing/Page",
            segment="Page",
            parent="/Missing",
            available_children=["Existing Page"],
        )
    )
    user = _UserDouble(notebook)

    with pytest.raises(TraversalError, match="missing child"):
        json_sync.download_json_files(
            user,
            notebook="My Notebook",
            page="Missing/Page",
            folder=Path("download-target"),
        )


def test_upload_json_files_returns_structured_results(tmp_path):
    """Test upload returns per-file results and preserves source filenames."""
    good_file = tmp_path / "config.json"
    good_file.write_text('{"enabled": true}', encoding="utf-8")
    bad_file = tmp_path / "broken.json"
    bad_file.write_text("{", encoding="utf-8")

    entries = _RecordingEntries()
    page = _PageDouble(entries)
    notebook = _RecordingContainer(traverse_result=_PageNode(page))
    user = _UserDouble(notebook)

    results = json_sync.upload_json_files(
        user,
        notebook="My Notebook",
        page="Results/Page",
        folder=tmp_path,
    )

    assert notebook.page_calls == ["Results/Page"]
    assert len(results) == 2
    assert sum(result.success for result in results) == 1
    assert entries.created_json == [({"enabled": True}, "config.json", "config")]
    assert {result.name for result in results} == {
        "broken.json",
        "config.json",
    }


def test_upload_json_files_skips_remote_page_when_folder_has_no_json(tmp_path):
    """Test upload returns before creating a LabArchives page when there is no work."""
    entries = _RecordingEntries()
    page = _PageDouble(entries)
    notebook = _RecordingContainer(traverse_result=_PageNode(page))
    user = _UserDouble(notebook)

    results = json_sync.upload_json_files(
        user,
        notebook="My Notebook",
        page="Results/Page",
        folder=tmp_path,
    )

    assert results == []
    assert notebook.page_calls == []


def test_upload_json_files_validates_folder(tmp_path):
    """Test upload raises a reusable error for missing local folders."""
    user = _UserDouble(_RecordingContainer())

    with pytest.raises(NotADirectoryError):
        json_sync.upload_json_files(
            user,
            notebook="My Notebook",
            page="Results/Page",
            folder=tmp_path / "missing",
        )


def test_download_json_files_writes_json_attachments_inside_target_folder(tmp_path):
    """Test download writes JSON-looking attachments inside the target folder."""
    json_entry = _make_attachment_entry(
        "entry-1",
        "../results.json",
        "application/octet-stream",
        b'{"score": 42}',
    )
    ignored_entry = _make_attachment_entry(
        "entry-2",
        "notes.txt",
        "text/plain",
        b'{"ignored": true}',
    )
    entries = _RecordingEntries([json_entry, ignored_entry])
    page = _PageDouble(entries)
    notebook = _RecordingContainer(traverse_result=_PageNode(page))
    user = _UserDouble(notebook)

    results = json_sync.download_json_files(
        user,
        notebook="My Notebook",
        page="Results/Page",
        folder=tmp_path,
    )

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].name == "results.json"
    assert results[0].path == tmp_path / "results.json"
    assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8")) == {
        "score": 42
    }


def test_download_json_files_reports_duplicate_basenames_without_overwriting(tmp_path):
    """Attachments normalizing to the same basename must not silently overwrite."""
    first = _make_attachment_entry(
        "entry-1",
        "same.json",
        "application/json",
        b'{"value": 1}',
    )
    second = _make_attachment_entry(
        "entry-2",
        "../same.json",
        "application/json",
        b'{"value": 2}',
    )
    entries = _RecordingEntries([first, second])
    page = _PageDouble(entries)
    notebook = _RecordingContainer(traverse_result=_PageNode(page))
    user = _UserDouble(notebook)

    results = json_sync.download_json_files(
        user,
        notebook="My Notebook",
        page="Results/Page",
        folder=tmp_path,
    )

    assert len(results) == 2
    assert results[0].name == "same.json"
    assert results[0].success is True
    assert results[1].name == "same.json"
    assert results[1].success is False
    assert results[1].error is not None
    assert "Duplicate" in results[1].error
    # The first payload is preserved, not overwritten by the second.
    assert json.loads((tmp_path / "same.json").read_text(encoding="utf-8")) == {
        "value": 1
    }


def test_download_json_files_records_failure_and_continues(tmp_path):
    """A failed attachment retrieval is recorded per-entry; later entries still process."""
    failing_entry = _make_failing_attachment_entry("bad-entry")
    good_entry = _make_attachment_entry(
        "good-entry",
        "results.json",
        "application/json",
        b'{"score": 42}',
    )
    entries = _RecordingEntries([failing_entry, good_entry])
    page = _PageDouble(entries)
    notebook = _RecordingContainer(traverse_result=_PageNode(page))
    user = _UserDouble(notebook)

    results = json_sync.download_json_files(
        user,
        notebook="My Notebook",
        page="Results/Page",
        folder=tmp_path,
    )

    assert len(results) == 2
    assert results[0].name == "bad-entry"
    assert results[0].success is False
    assert results[0].error == "content unavailable"
    assert results[1].name == "results.json"
    assert results[1].success is True
    assert json.loads((tmp_path / "results.json").read_text(encoding="utf-8")) == {
        "score": 42
    }


def test_main_upload_reports_summary_and_failures(tmp_path, monkeypatch, capsys):
    """Test the CLI keeps output minimal while reporting failed files."""
    good_file = tmp_path / "config.json"
    good_file.write_text('{"enabled": true}', encoding="utf-8")
    bad_file = tmp_path / "broken.json"
    bad_file.write_text("{", encoding="utf-8")

    entries = _RecordingEntries()
    page = _PageDouble(entries)
    user = _UserDouble(_RecordingContainer(traverse_result=_PageNode(page)))
    monkeypatch.setattr(json_sync, "Client", lambda: _ClientDouble(user))

    exit_code = json_sync.main(
        [
            "upload",
            str(tmp_path),
            "Results/Page",
            "--notebook",
            "My Notebook",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Uploaded 1/2 files" in captured.out
    assert "Could not upload broken.json: Invalid JSON" in captured.out
    assert "Uploaded config.json" not in captured.out
