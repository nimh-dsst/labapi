#!/usr/bin/env python3
"""Upload and download LabArchives HTML table entries as CSV."""

import argparse
import csv
import sys
from pathlib import Path

from bs4 import BeautifulSoup

from labapi import (
    Client,
    TextEntry,
    TraversalError,
    User,
)


def csv_to_html_table(
    csv_file: Path, has_header: bool = True
) -> str:  # TODO block injection
    """Convert a CSV file to an HTML table.

    :param csv_file: Path to the CSV file
    :param has_header: Whether the first row is a header
    :returns: HTML string containing the table
    """
    with csv_file.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return "<p>Empty CSV file</p>"

    html_parts = ["<table>"]

    # Process header row
    if has_header and rows:
        html_parts.append("  <thead>")
        html_parts.append("    <tr>")
        for cell in rows[0]:
            html_parts.append(f"      <th>{cell}</th>")
        html_parts.append("    </tr>")
        html_parts.append("  </thead>")
        rows = rows[1:]  # Remove header from data rows

    # Process data rows
    if rows:
        html_parts.append("  <tbody>")
        for row in rows:
            html_parts.append("    <tr>")
            for cell in row:
                html_parts.append(f"      <td>{cell}</td>")
            html_parts.append("    </tr>")
        html_parts.append("  </tbody>")

    html_parts.append("</table>")

    return "\n".join(html_parts)


def html_table_to_csv(html: str, output_file: Path) -> bool:
    """Extract HTML tables from HTML content and save as CSV.

    :param html: HTML content containing tables
    :param output_file: Path to save the CSV file
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")

    if not tables:
        print("No tables found in HTML content")
        return False

    if len(tables) > 1:
        print(f"Warning: Found {len(tables)} tables, using the first one")

    table = tables[0]
    rows: list[list[str]] = []

    # Extract header if present
    thead = table.find("thead")
    if thead:
        header_row = thead.find("tr")
        if header_row:
            headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
            rows.append(headers)

    # Extract body rows
    tbody = table.find("tbody")
    if tbody:
        for tr in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            rows.append(cells)
    else:
        # No tbody, just get all tr elements after thead
        for tr in table.find_all("tr"):
            # Skip if this is the header row we already processed
            if thead and tr in thead.find_all("tr"):
                continue
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells:
                rows.append(cells)

    # Write to CSV
    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    return True


def upload_csv_as_table(
    user: User,
    notebook_name: str,
    csv_file: Path,
    page_path: str,
    has_header: bool = True,
) -> None:
    """Upload a CSV file as an HTML table to a LabArchives page."""
    if not csv_file.exists():
        print(f"Error: CSV file '{csv_file}' does not exist")
        sys.exit(1)

    notebooks = user.notebooks
    try:
        notebook = notebooks[notebook_name]
        print(f"Ensuring page path exists: {page_path}")
        page = notebook.page(page_path)
    except (KeyError, TraversalError, TypeError, ValueError) as e:
        print(f"Error: Could not access or create path '{page_path}': {e}")
        sys.exit(1)

    print(f"Converting '{csv_file}' to HTML table...")
    html_table = csv_to_html_table(csv_file, has_header=has_header)

    print(f"Uploading table to '{page_path}'...")
    try:
        entry = page.entries.create(TextEntry, html_table)
        print(f"✓ Table uploaded successfully (Entry ID: {entry.id})")
    except Exception as e:
        print(f"✗ Error uploading table: {e}")
        sys.exit(1)


def download_table_as_csv(
    user: User,
    notebook_name: str,
    page_path: str,
    output_file: Path,
    entry_index: int = -1,
) -> None:
    """Download an HTML table from a LabArchives page as a CSV file."""
    notebooks = user.notebooks
    try:
        notebook = notebooks[notebook_name]
    except KeyError as e:
        print(f"Error: Could not find notebook '{notebook_name}': {e}")
        print(f"Available notebooks: {list(notebooks.keys())}")
        sys.exit(1)
    try:
        page = notebook.traverse(page_path).as_page()
    except TraversalError as e:
        print(
            f"Error: Could not find page '{page_path}' in notebook '{notebook_name}': {e}"
        )
        sys.exit(1)
    except TypeError:
        print(f"Error: '{page_path}' refers to a directory, but a page is required")
        sys.exit(1)

    entries = page.entries

    # Find text entries that contain tables
    table_entries: list[tuple[int, TextEntry]] = [
        (i, e)
        for i, e in enumerate(entries)
        if isinstance(e, TextEntry) and "<table" in e.content.lower()
    ]

    if not table_entries:
        print(f"No table entries found on page '{page_path}'")
        print("Note: Only text entries containing <table> tags are considered")
        sys.exit(1)

    print(f"Found {len(table_entries)} entry/entries with tables")

    # Select entry
    if entry_index == -1:
        # Use the most recent table entry
        entry_idx, entry = table_entries[-1]
        print(f"Using most recent table entry (entry {entry_idx + 1})")
    else:
        if entry_index >= len(entries):
            print(
                f"Error: Entry index {entry_index} out of range (page has {len(entries)} entries)"
            )
            sys.exit(1)
        entry = entries[entry_index]
        if not isinstance(entry, TextEntry):
            print(f"Error: Entry {entry_index} is not a text entry")
            sys.exit(1)

    print("Extracting table from entry...")
    success = html_table_to_csv(entry.content, output_file)

    if success:
        print(f"✓ Table saved to '{output_file}'")
    else:
        print("✗ Failed to extract table")
        sys.exit(1)


def main() -> None:
    """Run the CSV table example CLI."""
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
        default=-1,
        help="Entry index to download (default: most recent table entry)",
    )
    parser.add_argument(
        "--no-header", action="store_true", help="CSV file has no header row"
    )

    args = parser.parse_args()

    print("Connecting to LabArchives...")
    try:
        with Client() as client:
            print("Authenticating...")
            user = client.default_authenticate()
            print("✓ Authenticated successfully")

            if args.action == "upload":
                csv_file = Path(args.file)
                page_path = args.target
                upload_csv_as_table(
                    user,
                    args.notebook,
                    csv_file,
                    page_path,
                    has_header=not args.no_header,
                )
            else:  # download
                page_path = args.file
                output_file = Path(args.target)
                download_table_as_csv(
                    user, args.notebook, page_path, output_file, args.entry_index
                )
    except Exception as e:
        print(f"Authentication error: {e}")
        print("\nMake sure you have a .env file with your credentials:")
        print("  ACCESS_KEYID=your_access_key_id")
        print("  ACCESS_PWD=your_password")
        sys.exit(1)


if __name__ == "__main__":
    main()
