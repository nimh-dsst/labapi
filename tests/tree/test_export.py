"""Tests for Notebook.export()."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from io import BytesIO
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest

import labapi as LA
from labapi.entry import Attachment, AttachmentEntry, PlainTextEntry, TextEntry
from labapi.exceptions import ApiError
from labapi.tree import notebook as notebook_module
from labapi.tree._export import _backup_tree, _walk_tree, _write_tree


def test_backup_tree_reads_sqlite_and_attachments(tmp_path):
    """The backup collector walks SQLite and stages every export file."""
    py7zr = pytest.importorskip("py7zr")
    backup = tmp_path / "backup" / "notebook"
    attachment = backup / "attachments" / "14" / "1" / "original" / "report.pdf"
    escaped_attachment = backup / "attachments" / "16" / "1" / "original" / "db.sqlite3"
    attachment.parent.mkdir(parents=True)
    attachment.write_bytes(b"attachment")
    escaped_attachment.parent.mkdir(parents=True)
    escaped_attachment.write_bytes(b"not the database")

    database = sqlite3.connect(backup / "db.sqlite3")
    database.executescript(
        """
        CREATE TABLE tree_nodes (
            id INTEGER PRIMARY KEY,
            parent_id INTEGER,
            relative_position REAL,
            entry_id INTEGER,
            display_text TEXT
        );
        CREATE TABLE entry_parts (
            id INTEGER PRIMARY KEY,
            entry_id INTEGER,
            part_type INTEGER,
            entry_data TEXT,
            relative_position REAL,
            attach_file_name TEXT,
            version INTEGER
        );
        INSERT INTO tree_nodes VALUES (1, 0, 1, -1, 'Folder');
        INSERT INTO tree_nodes VALUES (2, 1, 1, 10, NULL);
        INSERT INTO tree_nodes VALUES (3, 0, 2, -1, 'Empty');
        INSERT INTO tree_nodes VALUES (4, 1, 2, 16, NULL);
        INSERT INTO entry_parts VALUES (11, 10, 0, 'Page', 1, NULL, 1);
        INSERT INTO entry_parts VALUES (12, 10, 1, '<p>html</p>', 2, NULL, 1);
        INSERT INTO entry_parts VALUES (13, 10, 5, 'plain', 3, NULL, 1);
        INSERT INTO entry_parts VALUES (14, 10, 2, NULL, 4, 'report.pdf', 1);
        INSERT INTO entry_parts VALUES (15, 10, 99, 'raw', 5, NULL, 1);
        INSERT INTO entry_parts VALUES (16, 10, 2, NULL, 6, '../../../../db.sqlite3', 1);
        INSERT INTO entry_parts VALUES (17, 16, 0, 'Empty page', 1, NULL, 1);
        """
    )
    database.close()

    archive_path = tmp_path / "backup.7z"
    with py7zr.SevenZipFile(archive_path, "w") as archive:
        archive.write(backup / "db.sqlite3", "notebook/db.sqlite3")
        archive.write(attachment, "notebook/attachments/14/1/original/report.pdf")
        archive.write(
            escaped_attachment, "notebook/attachments/16/1/original/db.sqlite3"
        )

    class Notebook:
        def backup(self, destination, **_kwargs):
            shutil.copy2(archive_path, destination)
            return destination

    work = tmp_path / "work"
    work.mkdir()
    tree = _backup_tree(cast(LA.Notebook, Notebook()), work)
    exported = _write_tree(tree, tmp_path / "export")

    page = exported / "1_Folder" / "1_Page"
    assert (page / "1_text.html").read_text(encoding="utf-8") == "<p>html</p>"
    assert (page / "2_text.txt").read_text(encoding="utf-8") == "plain"
    assert (page / "3_report.pdf").read_bytes() == b"attachment"
    assert (page / "4_text.txt").read_text(encoding="utf-8") == "raw"
    assert (page / "5_db.sqlite3").read_bytes() == b"not the database"
    assert json.loads((page / ".labarchives.json").read_text(encoding="utf-8")) == {
        "id": "2",
        "entries": [
            {"file": "1_text.html", "id": "12", "type": "text entry"},
            {"file": "2_text.txt", "id": "13", "type": "plain text entry"},
            {
                "file": "3_report.pdf",
                "id": "14",
                "type": "Attachment",
                "filename": "report.pdf",
            },
            {"file": "4_text.txt", "id": "15", "type": "part type 99"},
            {
                "file": "5_db.sqlite3",
                "id": "16",
                "type": "Attachment",
                "filename": "db.sqlite3",
            },
        ],
    }
    assert (exported / "1_Folder" / "2_Empty page").is_dir()
    assert (exported / "2_Empty").is_dir()


def test_walk_tree_stages_all_entries(monkeypatch, tmp_path):
    """The live collector writes text and attachment entries to temporary files."""
    user = cast(LA.User, None)
    attachment_entry = AttachmentEntry("3", "caption", user)
    cached_attachment = Attachment(
        BytesIO(b"cached"), "text/plain", "cached.txt", "caption"
    )
    attachment_entry._filedata = cached_attachment
    monkeypatch.setattr(
        attachment_entry,
        "get_attachment",
        lambda **_kwargs: Attachment(
            BytesIO(b"attachment"), "text/plain", "report?.txt", "caption"
        ),
    )

    class Page:
        def __init__(self, name="Page", entries=None, page_id="10"):
            self.name = name
            self.id = page_id
            self.entries = (
                entries
                if entries is not None
                else [
                    TextEntry("1", "<p>html</p>", user),
                    PlainTextEntry("2", "plain", user),
                    attachment_entry,
                ]
            )

        @staticmethod
        def is_dir():
            return False

        def as_page(self):
            return self

    class Folder:
        def __init__(self):
            self.name = "Folder"
            self.children = [Page(), Page("Empty page", [], "11")]

        @staticmethod
        def is_dir():
            return True

        @staticmethod
        def as_dir():
            return Folder()

    class Notebook:
        def __init__(self):
            self.children = [Folder()]

    tree = _walk_tree(cast(LA.Notebook, Notebook()), tmp_path)
    exported = _write_tree(tree, tmp_path / "export")
    page = exported / "1_Folder" / "1_Page"

    assert (page / "1_text.html").read_text(encoding="utf-8") == "<p>html</p>"
    assert (page / "2_text.txt").read_text(encoding="utf-8") == "plain"
    assert (page / "3_report_.txt").read_bytes() == b"attachment"
    assert json.loads((page / ".labarchives.json").read_text(encoding="utf-8")) == {
        "id": "10",
        "entries": [
            {"file": "1_text.html", "id": "1", "type": "text entry"},
            {"file": "2_text.txt", "id": "2", "type": "plain text entry"},
            {
                "file": "3_report_.txt",
                "id": "3",
                "type": "Attachment",
                "filename": "report?.txt",
                "mime_type": "text/plain",
            },
        ],
    }
    assert json.loads(
        (exported / "1_Folder" / "2_Empty page" / ".labarchives.json").read_text(
            encoding="utf-8"
        )
    ) == {"id": "11", "entries": []}
    assert (exported / "1_Folder" / "2_Empty page").is_dir()
    assert cached_attachment.closed
    assert attachment_entry._filedata is None


def test_write_tree_creates_an_empty_notebook(tmp_path):
    """An empty export tree still creates the notebook directory."""
    exported = _write_tree({}, tmp_path / "export")

    assert exported.is_dir()
    assert not any(exported.iterdir())


def test_write_tree_shortens_an_overlong_filename(tmp_path):
    """The writer keeps every output component below Windows' filename limit."""
    source = tmp_path / "source.txt"
    source.write_text("contents", encoding="utf-8")

    exported = _write_tree({f"{'x' * 300}.txt": source}, tmp_path / "export")
    files = list(exported.iterdir())

    assert len(files) == 1
    assert len(files[0].name) <= 240
    assert files[0].suffix == ".txt"
    extended_file = Path("\\\\?\\" + str(files[0].resolve()))
    assert extended_file.read_text(encoding="utf-8") == "contents"


@pytest.mark.skipif(os.name != "nt", reason="uses Windows extended paths")
def test_write_tree_supports_a_long_windows_path(tmp_path):
    """The writer can create an export whose total path exceeds MAX_PATH."""
    source = tmp_path / "source.txt"
    source.write_text("contents", encoding="utf-8")
    names = [f"folder_{number:02}_{'x' * 30}" for number in range(8)]
    tree = {"source.txt": source}
    for name in reversed(names):
        tree = {name: tree}

    exported = _write_tree(tree, tmp_path / "export")
    target = exported.joinpath(*names, "source.txt")
    extended_target = Path("\\\\?\\" + str(target.resolve()))

    assert extended_target.read_text(encoding="utf-8") == "contents"


@pytest.mark.parametrize(
    "error", [ImportError(), ApiError("denied", 4547), ApiError("failed", 5000)]
)
def test_auto_falls_back_to_walk(monkeypatch, notebook: LA.Notebook, tmp_path, error):
    """Automatic exports fall back to the API tree when backup is unavailable."""
    monkeypatch.setattr(notebook_module, "_backup_tree", Mock(side_effect=error))
    monkeypatch.setattr(notebook_module, "_walk_tree", Mock(return_value={}))

    assert notebook.export(tmp_path / "export") == tmp_path / "export"


def test_backup_source_chains_the_backup_error(
    monkeypatch, notebook: LA.Notebook, tmp_path
):
    """Explicit backup exports retain the failure that prevented export."""
    error = ImportError("py7zr")
    monkeypatch.setattr(notebook_module, "_backup_tree", Mock(side_effect=error))

    with pytest.raises(RuntimeError, match="source='backup'") as raised:
        notebook.export(tmp_path / "export", source="backup")

    assert raised.value.__cause__ is error
