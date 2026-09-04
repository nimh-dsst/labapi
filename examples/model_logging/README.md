# Model Logging Example

This example demonstrates a structured way to log machine learning model metadata, metrics, and artifacts to LabArchives. It creates a hierarchical structure: `{notebook}/Model Log/{email}/{iso8601_timestamp}/`.

## Features

- **Automated Directory Structure:** Creates the necessary folder hierarchy automatically.
- **Metadata Logging:** Stores tags and git commit hashes as text entries.
- **Metrics Logging:** Saves performance metrics as JSON entries.
- **Artifact Storage:** Uploads results and figures as attachments.

## Dependencies

- `labapi[dotenv,builtin-auth]` for the documented local interactive workflow

Run installation commands from the repository root.

## Usage

```python
from labapi import Client
from model_logger import ModelLogger

with Client() as client:
    user = client.default_authenticate()
    logger = ModelLogger(notebook_name="My Research", user=user)
    logger.log(
        tags=["baseline", "resnet50", "imagenet"],
        metrics={"f1": 0.88, "accuracy": 0.92, "loss": 0.15},
        results=b"Prediction results data...",
        figures=[b"Figure 1 data...", b"Figure 2 data..."],
        commit="a1b2c3d4e5f6...",
    )
```

## Configuration

Requires a `.env` file in the project root with your LabArchives credentials:

```env
API_URL=https://api.labarchives.com
ACCESS_KEYID=your_access_key_id
ACCESS_PWD=your_password
```
