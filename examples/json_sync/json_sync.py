#!/usr/bin/env python3
"""Sync JSON files between local disk and a LabArchives page.

This example has two layers:

* ``upload_json_files`` and ``download_json_files`` are reusable functions. They
  take an authenticated :class:`labapi.User` and return structured results
  instead of printing or exiting.
* ``main`` is the command-line layer. It handles arguments, authentication,
  terminal output, and process exit codes.

For a first LabArchives API script, the important object chain is:

``Client()`` -> ``client.default_authenticate()`` -> ``User`` ->
``user.notebooks["Notebook Name"]`` -> ``page.entries``.

The ``User`` object represents the authenticated LabArchives account. A
notebook is a tree-like container of folders and pages. A page contains entries,
including attachment entries. JSON entries created by ``labapi`` are stored as
attachment entries, with an optional text preview beside them.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import cast

from labapi import (
    AttachmentEntry,
    Client,
    JsonData,
    User,
)


@dataclass(frozen=True, slots=True)
class FileResult:
    """Outcome for one local or remote JSON file.

    ``success`` lets callers decide whether to continue, retry, or fail the
    surrounding workflow. The CLI below prints a short summary, while imported
    code can inspect these results directly.
    """

    name: str
    path: Path
    success: bool
    error: str | None = None


def upload_json_files(
    user: User,
    notebook: str,
    page: str,
    folder: Path,
) -> list[FileResult]:
    """Upload every ``*.json`` file in ``folder`` to a LabArchives page.

    ``user`` is already authenticated, so this function does not know anything
    about credentials or command-line arguments. It only performs the sync work.

    ``notebook`` is the visible notebook name in LabArchives. ``page`` is a
    LabArchives page path inside that notebook, such as ``"Data/Results"``.
    ``folder`` is a local filesystem path.

    The target page is created if it does not already exist. Each valid JSON
    file becomes a LabArchives JSON entry through
    :meth:`labapi.entry.collection.Entries.create_json_entry`.
    """
    if not folder.is_dir():
        raise NotADirectoryError(folder)

    file_paths = sorted(folder.glob("*.json"))
    if not file_paths:
        return []

    # ``page`` is a convenience method from labapi. It ensures the page path
    # exists, creating any missing parent folders along the way.
    target_page = user.notebooks[notebook].page(page)
    results: list[FileResult] = []

    for file_path in file_paths:
        try:
            with file_path.open("r", encoding="utf-8") as file:
                data = cast(JsonData, json.load(file))
            # ``create_json_entry`` uploads the JSON as an attachment and
            # creates the companion preview entry used by LabArchives.
            target_page.entries.create_json_entry(
                data,
                filename=file_path.name,
                caption=file_path.stem,
            )
        except json.JSONDecodeError as exc:
            results.append(
                FileResult(file_path.name, file_path, False, f"Invalid JSON: {exc}")
            )
        except Exception as exc:
            results.append(FileResult(file_path.name, file_path, False, str(exc)))
        else:
            results.append(FileResult(file_path.name, file_path, True))

    return results


def download_json_files(
    user: User,
    notebook: str,
    page: str,
    folder: Path,
) -> list[FileResult]:
    """Download JSON attachment entries from a LabArchives page into ``folder``.

    Download is intentionally read-only for LabArchives. It traverses to an
    existing page, inspects that page's entries, and writes JSON attachments to
    local files.

    ``traverse(page).as_page()`` means "find this existing tree path and treat
    it as a page." This differs from ``page(page)``, which would create the page
    if it were missing.
    """
    # ``traverse`` finds an existing page. Missing pages raise TraversalError,
    # which callers can handle just like any other labapi error.
    source_page = user.notebooks[notebook].traverse(page).as_page()
    folder.mkdir(parents=True, exist_ok=True)
    results: list[FileResult] = []
    used_paths: set[Path] = set()

    # A page can contain text entries, widgets, attachments, and other entry
    # types. This example only downloads attachment entries that look like JSON.
    for entry in source_page.entries:
        if not isinstance(entry, AttachmentEntry):
            continue

        # ``entry.content`` downloads a fresh Attachment object. Close it when
        # finished so local file handles or temporary buffers are released.
        attachment = entry.content
        try:
            # Treat remote filenames as filenames, not paths. This keeps every
            # download inside ``folder`` even if a server-provided name includes
            # POSIX or Windows path separators.
            filename = PureWindowsPath(PurePosixPath(attachment.filename).name).name
            is_json = (
                attachment.mime_type == "application/json"
                or filename.lower().endswith(".json")
            )
            if not is_json:
                continue

            output_path = folder / filename
            # Two attachments can normalize to the same basename. Refuse to
            # overwrite an already-written file; report the collision instead
            # of silently replacing earlier data.
            if output_path in used_paths:
                results.append(
                    FileResult(
                        filename,
                        output_path,
                        False,
                        f"Duplicate attachment filename '{filename}'; "
                        "refusing to overwrite",
                    )
                )
                continue
            used_paths.add(output_path)

            try:
                attachment.seek(0)
                data = cast(JsonData, json.load(attachment))
                with output_path.open("w", encoding="utf-8") as file:
                    json.dump(data, file, indent=2)
            except Exception as exc:
                results.append(FileResult(filename, output_path, False, str(exc)))
            else:
                results.append(FileResult(filename, output_path, True))
        finally:
            attachment.close()

    return results


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    The positional arguments are intentionally simple:

    * upload: ``source`` is the local folder and ``destination`` is the page.
    * download: ``source`` is the page and ``destination`` is the local folder.
    """
    parser = argparse.ArgumentParser(
        description="Sync JSON files between a local folder and a LabArchives page"
    )
    parser.add_argument(
        "action",
        choices=["upload", "download"],
        help="Upload local JSON files or download LabArchives JSON entries",
    )
    parser.add_argument(
        "source",
        help="Local folder path for upload, or LabArchives page path for download",
    )
    parser.add_argument(
        "destination",
        help="LabArchives page path for upload, or local folder path for download",
    )
    parser.add_argument(
        "--notebook",
        "-n",
        required=True,
        help="Name of the LabArchives notebook to use",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the JSON sync example CLI.

    This function is the only place that authenticates, prints, or chooses a
    process exit code. Keeping those concerns here makes the upload/download
    functions safe to import from another script or test.
    """
    args = build_parser().parse_args(argv)

    try:
        with Client() as client:
            # ``default_authenticate`` uses the configured labapi auth flow. With
            # the dotenv extra, credentials can come from a local ``.env`` file.
            user = client.default_authenticate()

            if args.action == "upload":
                source_folder = Path(args.source)
                upload_results = upload_json_files(
                    user,
                    args.notebook,
                    args.destination,
                    source_folder,
                )
                if not upload_results:
                    print(f"No JSON files found in '{source_folder}'")
                    return 0

                successes = sum(result.success for result in upload_results)
                print(f"Uploaded {successes}/{len(upload_results)} files")

                for result in upload_results:
                    if not result.success:
                        print(f"Could not upload {result.name}: {result.error}")

                return 0 if all(result.success for result in upload_results) else 1

            destination_folder = Path(args.destination)
            download_results = download_json_files(
                user,
                args.notebook,
                args.source,
                destination_folder,
            )
            if not download_results:
                print(f"No JSON entries found on page '{args.source}'")
                return 0

            successes = sum(result.success for result in download_results)
            print(
                f"Downloaded {successes}/{len(download_results)} files "
                f"to '{destination_folder}'"
            )

            for result in download_results:
                if not result.success:
                    print(f"Could not download {result.name}: {result.error}")

            return 0 if all(result.success for result in download_results) else 1
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
