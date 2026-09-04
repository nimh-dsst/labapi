#!/usr/bin/env python3
"""Populate a LabArchives notebook with sample folder-download data."""

import argparse
import sys
from io import BytesIO

from labapi import (
    Attachment,
    AttachmentEntry,
    Client,
    HeaderEntry,
    NotebookDirectory,
    NotebookPage,
    PlainTextEntry,
    TextEntry,
    User,
)


def populate_notebook(user: User, notebook_name: str) -> None:
    """Populate a notebook with a nested structure and various entry types."""
    notebooks = user.notebooks
    try:
        notebook = notebooks[notebook_name]
    except KeyError:
        available = ", ".join(notebooks.keys())
        print(f"Error: Could not find notebook '{notebook_name}'")
        print(f"Available: {available}")
        sys.exit(1)

    print(f"Populating notebook '{notebook_name}'...")

    # 1. Create a top-level folder
    print("  Creating folder: Experiments")
    experiments = notebook.create(NotebookDirectory, "Experiments")

    # 2. Create a subfolder
    print("  Creating folder: 2024")
    year_folder = experiments.create(NotebookDirectory, "2024")

    # 3. Create a page with various entry types
    print("  Creating page: Experiment 1")
    page = year_folder.create(NotebookPage, "Experiment 1")

    # Add a heading
    print("    Adding heading...")
    page.entries.create(HeaderEntry, "Calibration Phase")

    # Add a text entry
    print("    Adding text entry...")
    page.entries.create(TextEntry, "<p>Initial calibration completed successfully.</p>")

    # Add an attachment
    print("    Adding attachment...")
    dummy_data = b"This is a dummy calibration report file content."
    attachment = Attachment(
        BytesIO(dummy_data),
        "text/plain",
        "calibration_report.txt",
        "Calibration report summary",
    )
    page.entries.create(AttachmentEntry, attachment)

    # 4. Create another page in a different folder
    print("  Creating page: General Notes")
    notes_page = experiments.create(NotebookPage, "General Notes")
    notes_page.entries.create(
        PlainTextEntry, "These are some general notes for the experiments folder."
    )

    print("\n✓ Notebook populated successfully!")
    print("\nYou can now test the download script:")
    print(
        f'  python folder_download.py --notebook "{notebook_name}" --path "Experiments" ./downloaded_data'
    )


def main() -> None:
    """Run the sample notebook population CLI."""
    parser = argparse.ArgumentParser(
        description="Populate a LabArchives notebook with test data"
    )
    parser.add_argument(
        "--notebook", "-n", required=True, help="Name of the notebook to populate"
    )
    args = parser.parse_args()

    print("Connecting to LabArchives...")
    try:
        with Client() as client:
            print("Authenticating...")
            user = client.default_authenticate()
            print("✓ Authenticated successfully")
            populate_notebook(user, args.notebook)
    # TODO(BLE001): intentional broad catch — top-level example handler: report the per-item failure and continue; narrow if a specific type becomes known.
    except Exception as e:  # noqa: BLE001
        print(f"Error authenticating: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
