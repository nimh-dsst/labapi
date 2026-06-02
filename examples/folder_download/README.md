# LabArchives Folder Download Example

This example demonstrates how to download a complete LabArchives folder structure to local disk, preserving the directory hierarchy. Pages become directories, and individual entries are saved as separate files.

`folder_download.py` contains reusable, typed download functions plus a small command-line interface.

## Dependencies

Install the example with the local authentication helpers:

- `labapi[dotenv,builtin-auth]` (the core library plus local auth helpers)

Run these commands from the repository root.

```bash
# Using uv (recommended)
uv sync --project examples/folder_download

# Using pip
pip install -e ".[dotenv,builtin-auth]"
```

## Usage

### Download entire notebook

```bash
# General usage from the repository root
uv run --project examples/folder_download python examples/folder_download/folder_download.py ./output --notebook "My Notebook"

# Quick test
uv run --project examples/folder_download python examples/folder_download/folder_download.py ./notebook_export --notebook "My Notebook"
```

### Download specific folder within a notebook

```bash
# General usage from the repository root
uv run --project examples/folder_download python examples/folder_download/folder_download.py ./output/2024_experiments --notebook "My Notebook" --path "Experiments/2024"

# Populate test data first (optional)
uv run --project examples/folder_download python examples/folder_download/populate_notebook.py --notebook "My Notebook"

# Download specific folder
uv run --project examples/folder_download python examples/folder_download/folder_download.py ./notebook_export --notebook "My Notebook" --path "Experiments"
```

## Options

- `--notebook`, `-n`: (Required) Name of the LabArchives notebook.
- `--path`, `-p`: Optional path within notebook (e.g., 'Experiments/2024'). If not specified, downloads entire notebook.
- `--overwrite`: Overwrite existing files if they exist in the output directory.

## Reusing the Download Logic

Import the download function when you want to compose the workflow from another script:

Most scripts only need `DownloadFolderOptions` and `download_notebook_or_folder`.

```python
from pathlib import Path

from labapi import Client
from examples.folder_download.folder_download import (
    DownloadFolderOptions,
    download_notebook_or_folder,
)

with Client() as client:
    user = client.default_authenticate()
    result = download_notebook_or_folder(
        user,
        DownloadFolderOptions(
            notebook_name="My Notebook",
            output_dir=Path("notebook_export"),
            path="Experiments",
        ),
    )

print(f"Downloaded {result.page_count} pages and {result.entry_count} entries")
```

The reusable function returns a `DownloadResult` with directory, page, entry, and error counts.

## Configuration

Requires a `.env` file in the project root with your LabArchives credentials.
The `.env` file is only auto-loaded when the `dotenv` extra is installed:

```env
ACCESS_KEYID=your_access_key_id
ACCESS_PWD=your_password
```
