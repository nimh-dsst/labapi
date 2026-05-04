# JSON Folder Sync Example

This example synchronizes JSON files between a local directory and a LabArchives page. Use it to upload a folder of local JSON files as LabArchives JSON entries, or to download JSON entries from LabArchives into local `.json` files.

`json_sync.py` contains reusable, typed upload and download functions plus a small command-line interface.

## Dependencies

Install the example with the local authentication helpers:

- `labapi[dotenv,builtin-auth]` (the core library plus local auth helpers)

Run these commands from the repository root.

```bash
# Using uv (recommended)
uv sync --project examples/json_sync

# Using pip
pip install -e ".[dotenv,builtin-auth]"
```

## Usage

### Upload all JSON files from local folder to LabArchives page

```bash
# General usage from the repository root
uv run --project examples/json_sync python examples/json_sync/json_sync.py upload /path/to/json/folder "Data/Results" --notebook "My Notebook"

# Quick test with sample data
uv run --project examples/json_sync python examples/json_sync/json_sync.py upload examples/json_sync/sample_data "Experiments/JSON Data" --notebook "My Notebook"
```

### Download all JSON entries from LabArchives page to local folder

```bash
# General usage from the repository root
uv run --project examples/json_sync python examples/json_sync/json_sync.py download "Data/Results" /path/to/output/folder --notebook "My Notebook"

# Quick test
uv run --project examples/json_sync python examples/json_sync/json_sync.py download "Experiments/JSON Data" ./downloaded_json --notebook "My Notebook"
```

## Options

- `--notebook`, `-n`: (Required) Name of the LabArchives notebook.

## Reusing the Sync Logic

Import the sync function when you want to compose the workflow from another script:

```python
from pathlib import Path

from labapi import Client
from examples.json_sync.json_sync import upload_json_files

with Client() as client:
    user = client.default_authenticate()
    results = upload_json_files(
        user,
        notebook="My Notebook",
        page="Experiments/JSON Data",
        folder=Path("examples/json_sync/sample_data"),
    )

uploaded = sum(result.success for result in results)
print(f"Uploaded {uploaded}/{len(results)} JSON files")
```

The reusable functions return one `FileResult` for each file they try to sync.

## Configuration

Create a `.env` file in the project root with your LabArchives credentials.
With the `dotenv` extra installed, `labapi` loads this file automatically:

```env
ACCESS_KEYID=your_access_key_id
ACCESS_PWD=your_password
```
