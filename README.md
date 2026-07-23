# labapi

A Python client for the LabArchives API.

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/nimh-dsst/labapi/actions/workflows/unit_tests.yml/badge.svg?branch=main)](https://github.com/nimh-dsst/labapi/actions/workflows/unit_tests.yml)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.19599400.svg)](https://doi.org/10.5281/zenodo.19599400)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/license/MIT)

`labapi` authenticates with LabArchives, navigates notebook trees, and creates or updates notebook content from Python.

[Source](https://github.com/nimh-dsst/labapi) | [Docs](https://nimh-dsst.github.io/labapi/) | [Issues](https://github.com/nimh-dsst/labapi/issues)

## Start Here

- New to `labapi`? Follow the [First Success Tutorial](https://nimh-dsst.github.io/labapi/latest/quick_start/tutorial.html) to install `labapi`, authenticate, and create your first LabArchives entry.
- Already using `labapi`? Jump to the [Quick Start](https://nimh-dsst.github.io/labapi/latest/quick_start/index.html), [User Guide](https://nimh-dsst.github.io/labapi/latest/guide/index.html), [Examples](https://nimh-dsst.github.io/labapi/latest/examples/index.html), or [FAQ](https://nimh-dsst.github.io/labapi/latest/faq.html).
- Working on the package itself? Start with [CONTRIBUTING.md](https://github.com/nimh-dsst/labapi/blob/main/CONTRIBUTING.md).

## Install

Requirements:

- Python 3.10+
- `uv` (recommended) or `pip`

Recommended install for local use:

```bash
uv add "labapi[dotenv,builtin-auth]"
# or
pip install "labapi[dotenv,builtin-auth]"
```

Other install options:

```bash
# Minimal install
uv add labapi
# or
pip install labapi

# Minimal install plus .env loading
uv add "labapi[dotenv]"
# or
pip install "labapi[dotenv]"
```

Extras:

- `dotenv` loads `API_URL`, `ACCESS_KEYID`, and `ACCESS_PWD` from a local `.env` file.
- `builtin-auth` enables `default_authenticate()` to open the LabArchives login flow in a local browser.

## Configure Credentials

LabArchives issues API keys on request. Ask your institution's LabArchives site administrator or Enterprise Success Team contact to request API access, or contact [support@labarchives.com](mailto:support@labarchives.com). LabArchives provides the Access Key ID, Access Password, and the API base URL for your region.

Add your LabArchives API credentials to a `.env` file:

```env
API_URL=https://api.labarchives.com
ACCESS_KEYID=your_access_key_id
ACCESS_PWD=your_access_password
```

Or set them directly in your shell:

```bash
export API_URL=https://api.labarchives.com
export ACCESS_KEYID=your_access_key_id
export ACCESS_PWD=your_access_password
```

```powershell
$env:API_URL="https://api.labarchives.com"
$env:ACCESS_KEYID="your_access_key_id"
$env:ACCESS_PWD="your_access_password"
```

`.env` files are only auto-loaded when `python-dotenv` is installed, such as with `labapi[dotenv]`.

## Quick Start

```python
from datetime import datetime

from labapi import Client, NotebookPage, TextEntry

with Client() as client:
    user = client.default_authenticate()

    notebook_name = next(iter(user.notebooks))
    notebook = user.notebooks[notebook_name]
    page = notebook.create(
        NotebookPage,
        f"API tutorial - {datetime.now():%Y-%m-%d %H:%M:%S}",
    )
    page.entries.create(TextEntry, "<p>Hello from labapi!</p>")
```

## Common Tasks

Authenticate in a service or callback-based app:

```python
from labapi import Client

with Client() as client:
    auth_url = client.generate_auth_url(callback_url)
    # Redirect the user to auth_url, then read email + auth_code
    user = client.login(email, auth_code)
```

Create different entry types:

```python
from labapi import HeaderEntry, PlainTextEntry, TextEntry

page.entries.create(TextEntry, "<p>Rich text content</p>")
page.entries.create(HeaderEntry, "Final Conclusions")
page.entries.create(PlainTextEntry, "<p>Literal text</p>")
page.entries.create_json_entry({"yield": 0.85, "purity": "99%"})
```

Browse notebooks by name and path:

```python
for name in user.notebooks:
    print(name)

notebook = user.notebooks["My Research Notebook"]
page = notebook.traverse("Experiments/2026/Results")
```

## Documentation Map

- [First Success Tutorial](https://nimh-dsst.github.io/labapi/latest/quick_start/tutorial.html): install, authenticate, and create a first entry.
- [Quick Start](https://nimh-dsst.github.io/labapi/latest/quick_start/index.html): setup, navigation, page creation, uploads, and basic write operations.
- [Authentication Guide](https://nimh-dsst.github.io/labapi/latest/guide/auth.html): browser authentication, terminal/manual authentication, and callback URL authentication.
- [User Guide](https://nimh-dsst.github.io/labapi/latest/guide/index.html): paths, entries, API behavior, exceptions, limits, and architecture notes.
- [Examples](https://nimh-dsst.github.io/labapi/latest/examples/index.html): scripts for JSON sync, folder export, and CSV table updates.
- [FAQ](https://nimh-dsst.github.io/labapi/latest/faq.html): authentication, certificate, and environment troubleshooting.

## Development

Clone the repo and install development dependencies:

```bash
git clone https://github.com/nimh-dsst/labapi.git
cd labapi
uv sync --all-groups
pre-commit install --hook-type pre-commit --hook-type pre-push
```

Common checks:

```bash
uv run pytest
uv run ruff check --fix .
uv run ruff format .
uv run pyright
```

Integration tests are opt-in and require live credentials. See [CONTRIBUTING.md](https://github.com/nimh-dsst/labapi/blob/main/CONTRIBUTING.md) for the full setup, including `AUTH_EMAIL` and `AUTH_KEY`.

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/nimh-dsst/labapi/blob/main/LICENSE) file for details.
