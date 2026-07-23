"""Private support for :meth:`Notebook.export`."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
from contextlib import closing
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING

from labapi.entry import AttachmentEntry, TextEntry

_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_COMPONENT_LENGTH = 240

if TYPE_CHECKING:
    from .notebook import Notebook


def _writable_name(name: str) -> str:
    """Make a LabArchives name writable as one filesystem path component."""
    name = _INVALID_PATH_CHARS.sub("_", name).rstrip(" .") or "untitled"
    if len(name) <= _MAX_COMPONENT_LENGTH:
        return name

    digest = hashlib.sha256(name.encode()).hexdigest()[:12]
    suffix = Path(name).suffix[-(_MAX_COMPONENT_LENGTH - len(digest) - 1) :]
    stem_length = _MAX_COMPONENT_LENGTH - len(suffix) - len(digest) - 1
    return f"{name[:stem_length]}~{digest}{suffix}"


def _backup_tree(notebook: Notebook, tmpdir: Path) -> dict:
    """Build an export tree from the native backup archive."""
    from py7zr import SevenZipFile

    archive_path = notebook.backup(tmpdir / "notebook.7z", include_attachments=True)
    extracted = tmpdir / "extract"

    with SevenZipFile(archive_path, mode="r") as archive:
        targets = [
            name
            for name in archive.getnames()
            if name.endswith("/db.sqlite3")
            or ("/attachments/" in name and "/original/" in name)
        ]
        archive.extract(extracted, targets)

    backup = extracted / "notebook"
    entries = tmpdir / "entries"
    entries.mkdir()

    with sqlite3.connect(backup / "db.sqlite3") as database:
        database.row_factory = sqlite3.Row

        def walk(parent_id: int) -> dict:
            nodes = database.execute(
                "SELECT id, entry_id, display_text FROM tree_nodes "
                "WHERE parent_id = ? ORDER BY relative_position, id",
                (parent_id,),
            ).fetchall()
            tree = {}
            width = len(str(len(nodes)))

            for number, node in enumerate(nodes, 1):
                if node["entry_id"] == -1:
                    name = node["display_text"] or f"node_{node['id']}"
                    tree[f"{number:0{width}d}_{name}"] = walk(node["id"])
                    continue

                parts = database.execute(
                    "SELECT id, part_type, entry_data, attach_file_name, version "
                    "FROM entry_parts WHERE entry_id = ? "
                    "ORDER BY relative_position, id",
                    (node["entry_id"],),
                ).fetchall()
                title = (
                    next(
                        (
                            part["entry_data"]
                            for part in parts
                            if part["part_type"] == 0
                        ),
                        None,
                    )
                    or f"node_{node['id']}"
                )
                page = walk(node["id"])
                content = [part for part in parts if part["part_type"] != 0]
                entry_width = len(str(len(content)))
                metadata = []

                for entry_number, part in enumerate(content, 1):
                    prefix = f"{entry_number:0{entry_width}d}_"
                    entry_type = {
                        1: "text entry",
                        2: "Attachment",
                        5: "plain text entry",
                    }.get(part["part_type"], f"part type {part['part_type']}")

                    if part["part_type"] == 2:
                        original = (
                            backup
                            / "attachments"
                            / str(part["id"])
                            / str(part["version"])
                            / "original"
                        )
                        attachment_name = Path(part["attach_file_name"]).name
                        source = original / attachment_name
                        filename = _writable_name(prefix + attachment_name)
                        page[filename] = source
                        metadata.append(
                            {
                                "file": filename,
                                "id": str(part["id"]),
                                "type": entry_type,
                                "filename": attachment_name,
                            }
                        )
                        continue

                    suffix = "text.html" if part["part_type"] == 1 else "text.txt"
                    source = entries / f"{part['id']}.{suffix.rsplit('.', 1)[1]}"
                    source.write_text(part["entry_data"] or "", encoding="utf-8")
                    filename = prefix + suffix
                    page[filename] = source
                    metadata.append(
                        {"file": filename, "id": str(part["id"]), "type": entry_type}
                    )

                source = entries / f"{node['id']}.json"
                source.write_text(
                    json.dumps({"id": str(node["id"]), "entries": metadata}, indent=2)
                    + "\n",
                    encoding="utf-8",
                )
                page[".labarchives.json"] = source

                tree[f"{number:0{width}d}_{title}"] = page

            return tree

        return walk(0)


def _walk_tree(notebook: Notebook, tmpdir: Path) -> dict:
    """Build an export tree from the live API tree."""
    entries = tmpdir / "entries"
    entries.mkdir()

    def walk(container) -> dict:
        tree = {}
        nodes = container.children
        width = len(str(len(nodes)))

        for number, node in enumerate(nodes, 1):
            if node.is_dir():
                tree[f"{number:0{width}d}_{node.name}"] = walk(node.as_dir())
                continue

            page = node.as_page()
            page_entries = list(page.entries)
            entry_width = len(str(len(page_entries)))
            files = {}
            metadata = []

            for entry_number, entry in enumerate(page_entries, 1):
                prefix = f"{entry_number:0{entry_width}d}_"

                if isinstance(entry, AttachmentEntry):
                    source = entries / entry.id
                    try:
                        attachment = entry.get_attachment(use_tempfile=True)
                        with closing(attachment), source.open("wb") as file:
                            shutil.copyfileobj(attachment, file)
                    finally:
                        entry._release_attachment_cache()
                    filename = _writable_name(prefix + attachment.filename)
                    files[filename] = source
                    metadata.append(
                        {
                            "file": filename,
                            "id": entry.id,
                            "type": entry.content_type,
                            "filename": attachment.filename,
                            "mime_type": attachment.mime_type,
                        }
                    )
                    continue

                suffix = "text.html" if isinstance(entry, TextEntry) else "text.txt"
                source = entries / f"{entry.id}.{suffix.rsplit('.', 1)[1]}"
                source.write_text(str(entry.content), encoding="utf-8")
                filename = prefix + suffix
                files[filename] = source
                metadata.append(
                    {"file": filename, "id": entry.id, "type": entry.content_type}
                )

            source = entries / f"{page.id}.json"
            source.write_text(
                json.dumps({"id": page.id, "entries": metadata}, indent=2) + "\n",
                encoding="utf-8",
            )
            files[".labarchives.json"] = source

            tree[f"{number:0{width}d}_{page.name}"] = files

        return tree

    return walk(notebook)


def _write_tree(
    tree: dict, destination: str | PathLike[str], overwrite: bool = False
) -> Path:
    """Copy an export tree to ``destination``."""
    destination = Path(destination)
    filesystem_destination = destination
    if os.name == "nt" and not str(destination).startswith("\\\\?\\"):
        filesystem_destination = Path("\\\\?\\" + str(destination.resolve()))

    if filesystem_destination.exists():
        if not filesystem_destination.is_dir():
            raise FileExistsError(
                f"Export destination is not a directory: {destination}"
            )
        if any(filesystem_destination.iterdir()):
            if not overwrite:
                raise FileExistsError(f"Export destination is not empty: {destination}")
            shutil.rmtree(filesystem_destination)

    filesystem_destination.mkdir(parents=True, exist_ok=True)

    for name, source in tree.items():
        name = _writable_name(name)
        target = filesystem_destination / name

        if isinstance(source, Path):
            shutil.copy2(source, target)
        else:
            _write_tree(source, target)

    return destination
