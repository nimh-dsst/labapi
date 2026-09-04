#!/usr/bin/env python3
"""Download a LabArchives notebook folder tree to local disk.

This example has two layers:

* ``download_notebook_or_folder`` is the reusable function. It takes an
  authenticated :class:`labapi.User`, writes files to disk, and returns
  structured counts instead of printing or exiting.
* ``main`` is the command-line layer. It handles arguments, authentication,
  terminal output, overwrite checks, and process exit codes.

Most scripts that reuse this example only need to import
``DownloadFolderOptions`` and ``download_notebook_or_folder``.

For a first LabArchives API script, the important object chain is:

``Client()`` -> ``client.default_authenticate()`` -> ``User`` ->
``user.notebooks["Notebook Name"]`` -> ``notebook.traverse(path)`` ->
``page.entries``.

The ``User`` object represents the authenticated LabArchives account. A
notebook is a tree-like container of folders and pages. This example walks that
tree and writes pages, entries, attachments, and basic metadata to local files.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath

from labapi import (
    AbstractTreeContainer,
    AttachmentEntry,
    Client,
    Entry,
    HeaderEntry,
    NotebookPage,
    PlainTextEntry,
    TextEntry,
    User,
    WidgetEntry,
)


@dataclass(frozen=True)
class DownloadFolderOptions:
    """Inputs needed to export one notebook or notebook subtree."""

    notebook_name: str
    output_dir: Path
    path: str | None = None


@dataclass(frozen=True)
class EntryDownloadError:
    """Details for one entry that could not be exported."""

    entry_index: int
    entry_id: str
    content_type: str
    error: str
    error_file: Path


@dataclass(frozen=True)
class DownloadResult:
    """Summary of a folder-download export."""

    output_dir: Path
    directory_count: int = 0
    page_count: int = 0
    entry_count: int = 0
    errors: tuple[EntryDownloadError, ...] = ()

    @property
    def error_count(self) -> int:
        """Return the number of entries that failed during export."""
        return len(self.errors)

    def merge(self, other: DownloadResult) -> DownloadResult:
        """Return a combined result for adjacent export operations."""
        return DownloadResult(
            self.output_dir,
            self.directory_count + other.directory_count,
            self.page_count + other.page_count,
            self.entry_count + other.entry_count,
            self.errors + other.errors,
        )


def sanitize_filename(name: str) -> str:
    """Sanitize a name to be safe for filesystem use."""
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        name = name.replace(char, "_")

    name = name.strip(". ")
    if len(name) > 200:
        name = name[:200]

    return name or "untitled"


def _sanitize_remote_filename(name: str) -> str:
    """Return a filesystem-safe basename for a remote LabArchives filename."""
    filename = PureWindowsPath(PurePosixPath(name).name).name
    return sanitize_filename(filename)


def get_unique_path(
    base_dir: Path, name: str, used_paths: set[Path], unique_suffix: str
) -> Path:
    """Return a collision-safe path for a sanitized LabArchives name."""
    sanitized_name = sanitize_filename(name)
    candidate = base_dir / sanitized_name

    if candidate not in used_paths:
        used_paths.add(candidate)
        return candidate

    sanitized_suffix = sanitize_filename(unique_suffix)[:8] or "dup"
    candidate = base_dir / f"{sanitized_name}_{sanitized_suffix}"

    counter = 1
    while candidate in used_paths:
        candidate = base_dir / f"{sanitized_name}_{sanitized_suffix}_{counter}"
        counter += 1

    used_paths.add(candidate)
    return candidate


def _download_page(
    page: NotebookPage, output_dir: Path, used_paths: set[Path]
) -> DownloadResult:
    """Download one LabArchives page and its entries to a local directory."""
    page_dir = get_unique_path(output_dir, page.name, used_paths, page.id)
    page_dir.mkdir(parents=True, exist_ok=True)

    _write_page_metadata(page, page_dir)

    errors: list[EntryDownloadError] = []
    for index, entry in enumerate(page.entries, start=1):
        error = _download_entry(entry, index, page_dir)
        if error is not None:
            errors.append(error)

    return DownloadResult(
        output_dir=output_dir,
        page_count=1,
        entry_count=len(page.entries),
        errors=tuple(errors),
    )


def _download_directory(
    directory: AbstractTreeContainer, output_dir: Path, used_paths: set[Path]
) -> DownloadResult:
    """Recursively download a LabArchives directory and its contents."""
    directory_path = get_unique_path(
        output_dir, directory.name, used_paths, directory.id
    )
    directory_path.mkdir(parents=True, exist_ok=True)

    result = DownloadResult(output_dir=output_dir, directory_count=1)
    for child in directory.children:
        if child.is_dir():
            child_result = _download_directory(
                child.as_dir(), directory_path, used_paths
            )
        else:
            child_result = _download_page(child.as_page(), directory_path, used_paths)
        result = result.merge(child_result)

    return result


def download_notebook_or_folder(
    user: User, options: DownloadFolderOptions
) -> DownloadResult:
    """Download a notebook, folder, or page from LabArchives.

    The reusable function assumes ``user`` is already authenticated. It does not
    parse command-line arguments, print progress, or choose process exit codes.
    Missing notebooks, invalid paths, and other labapi errors propagate to the
    caller.
    """
    notebook = user.notebooks[options.notebook_name]
    target = notebook.traverse(options.path) if options.path else notebook
    options.output_dir.mkdir(parents=True, exist_ok=True)

    used_paths: set[Path] = set()
    if target.is_dir():
        return _download_directory(target.as_dir(), options.output_dir, used_paths)
    return _download_page(target.as_page(), options.output_dir, used_paths)


def _write_page_metadata(page: NotebookPage, page_dir: Path) -> None:
    """Write metadata for one downloaded page."""
    metadata_file = page_dir / "_metadata.txt"
    with metadata_file.open("w", encoding="utf-8") as handle:
        handle.write(f"Page: {page.name}\n")
        handle.write(f"ID: {page.id}\n")
        handle.write(f"Entry count: {len(page.entries)}\n")


def _download_entry(
    entry: Entry[object], entry_index: int, page_dir: Path
) -> EntryDownloadError | None:
    """Download one page entry and return error details when it fails."""
    try:
        _write_entry(entry, entry_index, page_dir)
    # TODO(BLE001): intentional broad catch — top-level example handler: report the per-item failure and continue; narrow if a specific type becomes known.
    except Exception as exc:  # noqa: BLE001
        error_file = page_dir / f"{entry_index:03d}_error.txt"
        with error_file.open("w", encoding="utf-8") as handle:
            handle.write(
                f"Error downloading entry {entry_index}: {exc}\n"
                f"Entry type: {entry.content_type}\n"
            )
        return EntryDownloadError(
            entry_index=entry_index,
            entry_id=entry.id,
            content_type=entry.content_type,
            error=str(exc),
            error_file=error_file,
        )
    return None


def _write_entry(entry: Entry[object], entry_index: int, page_dir: Path) -> None:
    """Write one LabArchives entry to disk."""
    entry_prefix = f"{entry_index:03d}"

    # Each LabArchives entry type gets a simple local representation that is
    # easy to inspect without re-running the API client.
    if isinstance(entry, AttachmentEntry):
        _write_attachment_entry(entry, entry_prefix, page_dir)
    elif isinstance(entry, HeaderEntry):
        _write_text_entry(entry, page_dir / f"{entry_prefix}_header.txt")
    elif isinstance(entry, TextEntry):
        _write_text_entry(entry, page_dir / f"{entry_prefix}_text.html")
    elif isinstance(entry, PlainTextEntry):
        _write_text_entry(entry, page_dir / f"{entry_prefix}_plaintext.txt")
    elif isinstance(entry, WidgetEntry):
        output_path = page_dir / f"{entry_prefix}_widget.txt"
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(
                f"Widget Entry (ID: {entry.id})\n"
                "Note: Widget entries are read-only and cannot be fully exported\n"
            )
    else:
        output_path = page_dir / f"{entry_prefix}_unknown.txt"
        with output_path.open("w", encoding="utf-8") as handle:
            handle.write(f"Unknown entry type: {entry.content_type}\n")
            handle.write(f"Entry ID: {entry.id}\n")


def _write_attachment_entry(
    entry: AttachmentEntry, entry_prefix: str, page_dir: Path
) -> None:
    """Write one attachment entry and optional caption to disk."""
    attachment = entry.content
    try:
        filename = _sanitize_remote_filename(attachment.filename)
        output_path = page_dir / f"{entry_prefix}_attachment_{filename}"
        with output_path.open("wb") as handle:
            attachment.seek(0)
            handle.write(attachment.read())
        if attachment.caption:
            caption_file = page_dir / f"{entry_prefix}_caption.txt"
            with caption_file.open("w", encoding="utf-8") as handle:
                handle.write(attachment.caption)
    finally:
        attachment.close()


def _write_text_entry(entry: PlainTextEntry, output_path: Path) -> None:
    """Write one text-like entry to disk."""
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(entry.content)


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Download LabArchives folder structure to local disk"
    )
    parser.add_argument("output", help="Local output directory path")
    parser.add_argument(
        "--notebook",
        "-n",
        required=True,
        help="Name of the LabArchives notebook to download from",
    )
    parser.add_argument(
        "--path",
        "-p",
        help=(
            "Optional path within notebook, for example 'Experiments/2024'. "
            "When omitted, downloads the entire notebook."
        ),
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing files"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line script and return a process exit code."""
    args = _build_parser().parse_args(argv)
    output_dir = Path(args.output)

    if output_dir.exists() and not args.overwrite and any(output_dir.iterdir()):
        print(f"Error: Output directory '{output_dir}' exists and is not empty")
        print("Use --overwrite to overwrite existing files")
        return 1

    try:
        with Client() as client:
            user = client.default_authenticate()
            result = download_notebook_or_folder(
                user,
                DownloadFolderOptions(
                    notebook_name=args.notebook,
                    output_dir=output_dir,
                    path=args.path,
                ),
            )
    # TODO(BLE001): intentional broad catch — top-level example handler: report the per-item failure and continue; narrow if a specific type becomes known.
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Downloaded {result.directory_count} directories, "
        f"{result.page_count} pages, and {result.entry_count} entries "
        f"to '{result.output_dir}'"
    )
    if result.error_count:
        print(f"{result.error_count} entries could not be fully exported")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
