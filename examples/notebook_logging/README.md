# Jupyter Notebook Logger Example

This example demonstrates how to use the `NotebookLogger` to capture and save your Jupyter Notebook experiments directly to LabArchives.

## Key Features

- **Interactive UI**: Save your work with a single click using an `ipywidgets` form.
- **Automatic Figure Capture**: All `matplotlib` figures displayed in your notebook are automatically captured and attached to the LabArchives page, even if `plt.show()` is called.
- **Explicit File Tracking**: Track and upload specific files (like CSV results) using `logger.track_file()`.
- **Run Metadata**: Automatically logs cell execution history, tags, and the last cell output.
- **Session Persistence**: Easily reuse authenticated user sessions to avoid re-logging in during a single notebook session.

## Setup

### Prerequisites

Ensure you have the following installed:

- `labapi[dotenv,builtin-auth]` (this package plus the documented local auth helpers)
- `ipywidgets`
- `matplotlib`
- `pandas`
- `numpy`
- `jupyter` or `jupyterlab`

### Installation

Run these commands from the repository root.

If you are using `uv`, you can run:

```bash
uv sync
```

Or with `pip`:

```bash
pip install ipywidgets matplotlib pandas numpy jupyter
pip install -e ".[dotenv,builtin-auth]"
```

## How to Use

1. **Initialize the Logger**:
   ```python
   from notebook_logger import NotebookLogger

   logger = NotebookLogger(notebook_name="Your LabArchives Notebook")
   ```

2. **Track Output Files**:
   If your code generates a file you want to save alongside your results:
   ```python
   df.to_csv("results.csv")
   logger.track_file("results.csv")
   ```

3. **Show the Save UI**:
   Display the tagging and save interface:
   ```python
   logger.show_ui()
   ```

## LabArchives Structure

Each "Save" creates a new page in your LabArchives notebook with the following structure:

`{Notebook Name}/Notebook Log/{User Email}/{ISO8601 Timestamp} (Page)`

The page includes:
- **Tags**: Styled labels for easy filtering.
- **Cell Info**: Recent execution history and count.
- **Result**: The string representation of your last cell's output.
- **Attachments**: Captured figures and any tracked files.

## Re-importing/Developing

If you modify the `notebook_logger.py` script and need to re-import it, you can reuse your existing authentication to skip the browser login:

```python
import importlib
import notebook_logger

importlib.reload(notebook_logger)

# Reuse existing user if already defined
user = logger.user if "logger" in locals() else None

logger = NotebookLogger(notebook_name="Your Notebook", user=user)
```
