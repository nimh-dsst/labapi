# CSV Table Upload/Download Example

This example demonstrates how to upload CSV files as rich text HTML tables in LabArchives, then download those tables back as CSV files. It is useful for displaying tabular data in a formatted, readable way while keeping a machine-friendly export path.

The example lives in `csv_table.py`.

## Dependencies

This example requires the following packages:

- `labapi[dotenv,builtin-auth]` (the core library plus local auth helpers)
- `beautifulsoup4` (for HTML parsing)

Use the example project with `uv`:

```bash
cd examples/csv_table
uv sync
```

Or install the same dependencies with pip from the repository root:

```bash
pip install -e ".[dotenv,builtin-auth]" beautifulsoup4
```

## Usage

### Upload CSV as HTML table

```bash
# From examples/csv_table
uv run python csv_table.py upload data.csv "Results/Table 1" --notebook "My Notebook"

# Quick test with sample data
uv run python csv_table.py upload sample_data.csv "Experiments/Sample Table" --notebook "My Notebook"
```

### Download HTML table as CSV

```bash
# From examples/csv_table
uv run python csv_table.py download "Results/Table 1" output.csv --notebook "My Notebook"

# Quick test
uv run python csv_table.py download "Experiments/Sample Table" downloaded_table.csv --notebook "My Notebook"
```

## Options

- `--notebook`, `-n`: (Required) Name of the LabArchives notebook.
- `--entry-index`: Entry index to download (default: most recent table entry).
- `--no-header`: Treat every CSV row as table data.

## Configuration

Requires a `.env` file in the project root with your LabArchives credentials.
The `.env` file is only auto-loaded when the `dotenv` extra is installed:

```env
ACCESS_KEYID=your_access_key_id
ACCESS_PWD=your_password
```
