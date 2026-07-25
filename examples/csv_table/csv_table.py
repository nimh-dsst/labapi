#!/usr/bin/env python3
"""Upload and download LabArchives rich-text tables as CSV.

This example keeps the LabArchives API usage deliberately visible:

- A :class:`labapi.Client` owns the HTTP session.
- ``client.default_authenticate()`` returns a :class:`labapi.User`.
- ``user.notebooks[name]`` selects a notebook by name.
- ``notebook.page(path)`` ensures an upload page exists.
- ``notebook.traverse(path).as_page()`` finds an existing download page.
- ``page.entries.create(TextEntry, html)`` creates a rich-text entry.

LabArchives rich-text entries can contain simple HTML, so this script converts
CSV rows into a ``<table>`` before upload and parses the first ``<table>`` from
a text entry when downloading.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Final, TypeAlias

from bs4 import BeautifulSoup
from bs4.element import Tag

from labapi import Client, NotebookPath, TextEntry, User
from labapi.entry import Entries

_CsvRow: TypeAlias = tuple[str, ...]
_CsvRows: TypeAlias = tuple[_CsvRow, ...]
_NotebookLocation: TypeAlias = str | NotebookPath
_TagNames: TypeAlias = str | Sequence[str]

_RECENT_TABLE_ENTRY: Final = -1


@dataclass(frozen=True)
class _CsvTable:
    """CSV-shaped data shared by the CSV reader, HTML renderer, and writer.

    ``headers`` is ``None`` when every CSV row should be treated as data.
    ``rows`` always contains body rows only.
    """

    headers: _CsvRow | None
    rows: _CsvRows

    @property
    def row_count(self) -> int:
        """Return the number of body rows."""
        return len(self.rows)

    @property
    def column_count(self) -> int:
        """Return the widest row width, including headers."""
        widths = [len(row) for row in self.rows]
        if self.headers is not None:
            widths.append(len(self.headers))
        return max(widths, default=0)


@dataclass(frozen=True)
class UploadTableOptions:
    """Inputs needed to upload one CSV file into one LabArchives page.

    ``page_path`` is a LabArchives notebook path such as ``"Results/Table 1"``.
    The upload path is created by ``notebook.page(...)`` if needed.
    """

    notebook_name: str
    csv_file: Path
    page_path: _NotebookLocation
    has_header: bool = True


@dataclass(frozen=True)
class _UploadTableResult:
    """Small result object used by the CLI success message."""

    entry_id: str
    row_count: int
    column_count: int


@dataclass(frozen=True)
class DownloadTableOptions:
    """Inputs needed to download one table entry from one LabArchives page.

    ``entry_index`` is zero-based. The default selects the most recent text
    entry on the page that contains an HTML ``<table>``.
    """

    notebook_name: str
    page_path: _NotebookLocation
    output_file: Path
    entry_index: int = _RECENT_TABLE_ENTRY


@dataclass(frozen=True)
class _DownloadTableResult:
    """Small result object used by the CLI success message."""

    entry_index: int
    row_count: int
    column_count: int


def upload_table(user: User, options: UploadTableOptions) -> _UploadTableResult:
    """Upload a CSV file as a LabArchives rich-text table entry.

    The core labapi calls are:

    1. ``user.notebooks[name]`` to choose the notebook.
    2. ``notebook.page(path)`` to get or create the destination page.
    3. ``page.entries.create(TextEntry, html)`` to add the rich-text table.
    """
    table = _read_csv_table(options.csv_file, has_header=options.has_header)

    # Notebooks behave like mappings. A string key selects the first notebook
    # with that name, matching the common quick-start style used in the docs.
    page = user.notebooks[options.notebook_name].page(options.page_path)

    # TextEntry is LabArchives' rich-text entry type. Passing HTML here lets the
    # table render in the web UI instead of appearing as plain text.
    entry = page.entries.create(TextEntry, _render_html_table(table))
    return _UploadTableResult(entry.id, table.row_count, table.column_count)


def download_table(user: User, options: DownloadTableOptions) -> _DownloadTableResult:
    """Download a LabArchives rich-text table entry as a CSV file.

    Download uses ``traverse(...).as_page()`` instead of ``page(...)`` so it
    reads from an existing page and lets labapi report path mistakes normally.
    """
    # ``traverse`` returns a generic tree node. ``as_page`` narrows it to a page
    # and raises TypeError if the path points at a folder.
    page = user.notebooks[options.notebook_name].traverse(options.page_path).as_page()
    entry_index, entry = _select_table_entry(page.entries, options.entry_index)
    table = _parse_html_table(entry.content)
    _write_csv_table(table, options.output_file)
    return _DownloadTableResult(entry_index, table.row_count, table.column_count)


def _read_csv_table(csv_file: Path, *, has_header: bool = True) -> _CsvTable:
    """Read a CSV file into the internal table shape.

    This intentionally uses Python's ``csv`` module so quoted commas, newlines,
    and other CSV details are handled by the standard library.
    """
    with csv_file.open("r", newline="", encoding="utf-8") as handle:
        rows: _CsvRows = tuple(tuple(row) for row in csv.reader(handle))

    if not rows:
        return _CsvTable(None, ())
    if has_header:
        return _CsvTable(rows[0], rows[1:])
    return _CsvTable(None, rows)


def _render_html_table(table: _CsvTable) -> str:
    """Render table data as simple HTML accepted by LabArchives rich text.

    Cell values are escaped before insertion so input such as ``<ok>`` is shown
    as text instead of becoming markup.
    """
    if table.headers is None and not table.rows:
        return "<p>Empty CSV file</p>"

    html = ["<table>"]
    if table.headers is not None:
        html.extend(["  <thead>", "    <tr>"])
        html.extend(f"      <th>{escape(cell)}</th>" for cell in table.headers)
        html.extend(["    </tr>", "  </thead>"])

    if table.rows:
        html.append("  <tbody>")
        for row in table.rows:
            html.append("    <tr>")
            html.extend(f"      <td>{escape(cell)}</td>" for cell in row)
            html.append("    </tr>")
        html.append("  </tbody>")

    html.append("</table>")
    return "\n".join(html)


def _parse_html_table(html: str) -> _CsvTable:
    """Parse the first HTML table from a rich-text entry.

    LabArchives stores rich-text entry content as HTML. BeautifulSoup gives this
    example a forgiving parser for markup copied from existing entries.
    """
    table_node = BeautifulSoup(html, "html.parser").find("table")
    if not isinstance(table_node, Tag):
        raise ValueError("No tables found in HTML content")

    # Prefer an explicit table header when present. Tables without ``thead`` are
    # still supported by treating every row as body data.
    thead = table_node.find("thead")
    header_row = thead.find("tr") if isinstance(thead, Tag) else None
    headers = _cell_texts(_find_tags(header_row, "th")) if header_row else None

    rows: list[_CsvRow] = []
    data_rows = table_node.find("tbody")
    source_node = data_rows if isinstance(data_rows, Tag) else table_node
    header_rows = _find_tags(thead, "tr") if isinstance(thead, Tag) else ()
    for tr in _find_tags(source_node, "tr"):
        # When there is no ``tbody``, ``source_node`` is the whole table. Skip
        # header rows we already collected so they are not written twice.
        if any(tr is header for header in header_rows):
            continue
        row = _cell_texts(_find_tags(tr, ["td", "th"]))
        if row:
            rows.append(row)

    return _CsvTable(headers or None, tuple(rows))


def _write_csv_table(table: _CsvTable, output_file: Path) -> None:
    """Write the internal table shape to a UTF-8 CSV file."""
    rows: list[_CsvRow] = []
    if table.headers is not None:
        rows.append(table.headers)
    rows.extend(table.rows)

    with output_file.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows(rows)


def _build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Upload CSV files as HTML tables or download HTML tables as CSV"
    )
    parser.add_argument(
        "action", choices=["upload", "download"], help="Action to perform"
    )
    parser.add_argument(
        "file", help="CSV file (upload) or LabArchives page path (download)"
    )
    parser.add_argument(
        "target", help="LabArchives page path (upload) or output CSV file (download)"
    )
    parser.add_argument(
        "--notebook",
        "-n",
        required=True,
        help="Name of the LabArchives notebook to use",
    )
    parser.add_argument(
        "--entry-index",
        type=int,
        default=_RECENT_TABLE_ENTRY,
        help="Zero-based page entry index to download (default: latest table entry)",
    )
    parser.add_argument(
        "--no-header", action="store_true", help="Treat every CSV row as table data"
    )
    return parser


def _run(argv: Sequence[str] | None = None) -> int:
    """Run the command-line script and return a process exit code.

    The CLI owns authentication, printing, and error-to-exit-code conversion.
    The upload/download helpers stay quiet so they are easy to test.
    """
    args = _build_parser().parse_args(argv)

    try:
        # Client is a context manager so the HTTP session is closed even when an
        # API call raises an exception.
        with Client() as client:
            # default_authenticate reads the usual labapi credential settings
            # documented in the quick start, including dotenv support when the
            # extra is installed.
            user = client.default_authenticate()

            if args.action == "upload":
                options = UploadTableOptions(
                    notebook_name=args.notebook,
                    csv_file=Path(args.file),
                    page_path=args.target,
                    has_header=not args.no_header,
                )
                result = upload_table(user, options)
                print(
                    f"Uploaded {result.row_count} rows x {result.column_count} columns "
                    f"as entry {result.entry_id}"
                )
            else:
                options = DownloadTableOptions(
                    notebook_name=args.notebook,
                    page_path=args.file,
                    output_file=Path(args.target),
                    entry_index=args.entry_index,
                )
                result = download_table(user, options)
                print(
                    f"Saved {result.row_count} rows x {result.column_count} columns "
                    f"from entry {result.entry_index + 1} to {options.output_file}"
                )

        return 0
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1


def _select_table_entry(
    entries: Entries, entry_index: int = _RECENT_TABLE_ENTRY
) -> tuple[int, TextEntry]:
    """Return the requested text entry that contains an HTML table."""
    if entry_index == _RECENT_TABLE_ENTRY:
        # Entries is a labapi sequence. Reversing it checks the newest entries
        # first while preserving the original page index for user-facing output.
        for offset, entry in enumerate(reversed(entries), start=1):
            if isinstance(entry, TextEntry) and "<table" in entry.content.lower():
                return len(entries) - offset, entry
        raise ValueError("No text entries containing <table> tags were found")

    if entry_index < 0:
        raise ValueError(
            f"Entry index {entry_index} is invalid; use {_RECENT_TABLE_ENTRY} for latest"
        )

    entry = entries[entry_index]
    if not isinstance(entry, TextEntry):
        raise TypeError(f"Entry {entry_index} is not a text entry")
    if "<table" not in entry.content.lower():
        raise ValueError(f"Entry {entry_index} does not contain a table")
    return entry_index, entry


def _find_tags(node: Tag, names: _TagNames) -> tuple[Tag, ...]:
    """Find child tags and discard non-tag BeautifulSoup nodes."""
    return tuple(tag for tag in node.find_all(names) if isinstance(tag, Tag))


def _cell_texts(cells: Sequence[Tag]) -> _CsvRow:
    """Return stripped visible text from table cell tags."""
    return tuple(cell.get_text(" ", strip=True) for cell in cells)


def main() -> None:
    """Run the CSV table example as a process."""
    raise SystemExit(_run())


if __name__ == "__main__":
    main()
