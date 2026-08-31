# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Important:** Check `.environment-setup` if it exists - it contains host-specific instructions (e.g., using Nix instead of uv).

## Project Overview

`labapi` is a Python client library for the LabArchives API, providing an object-oriented interface for managing notebooks, folders, pages, and entries. The LabArchives API uses XML, and requests are signed with HMAC-SHA512.

## Build & Development Commands

```bash
# Setup (using uv)
uv sync
source .venv/bin/activate

# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_unit.py
pytest tests/test_integration.py  # requires AUTH_EMAIL and AUTH_KEY env vars

# Lint and format
ruff check .
ruff format .
ruff check --fix .  # auto-fix linting issues
```

## Architecture

The codebase follows a hierarchical tree structure mirroring LabArchives organization:

**Core modules:**
- `src/labapi/client.py` - Main API client with HMAC-SHA512 request signing, authentication flows (`generate_auth_url`, `login_authcode`), and `api_get`/`api_post` methods
- `src/labapi/user.py` - Authenticated user session; provides access to notebooks via `user.notebooks`
- `src/labapi/tree/` - Hierarchical data model: `Notebook` → `NotebookDirectory` → `NotebookPage`
- `src/labapi/entry/` - Entry types on pages: `TextEntry`, `HeaderEntry`, `PlainTextEntry`, `AttachmentEntry`, `WidgetEntry`
- `src/labapi/util/extract.py` - XML extraction helpers (`extract_etree`, `to_bool`, `_flatten_dict`)
- `src/labapi/util/index.py` - Indexing enum for accessing items by ID or name: `notebook[Index.Id:"some_id"]` or `notebook[Index.Name:"some_name"]`

**Entry point pattern:**
```python
from labapi import Client
client = Client(base_url, akid, password)  # or Client() to load from .env
auth_url = client.generate_auth_url(redirect_url)
user = client.login_authcode(user_email, auth_code)
notebooks = user.notebooks
```

## Development Conventions

- **Type hinting:** All new code must be fully type-hinted
- **XML handling:** Use `lxml` for all XML parsing; use helpers in `src/labapi/util/extract.py`
- **Testing:** Prefer unit tests with `MockClient` (in `tests/test_unit.py`) over integration tests to avoid hitting the live API
- **Error handling:** API errors are raised as `RuntimeError` (future: type these more specifically)

## Environment Variables

The `Client` class auto-loads from a `.env` file via `python-dotenv` when credentials aren't passed directly. Create a `.env` file (gitignored) with:

```bash
API_URL=https://api.labarchives.com  # optional, this is the default
ACCESS_KEYID=your_akid               # required
ACCESS_PWD=your_password             # required
```

**Other environment variables:**
- `AUTH_EMAIL`, `AUTH_KEY` - Required for non-interactive integration test login
- `LA_AUTH_BROWSER` - Browser for OAuth flows (chrome, firefox, edge)
- `AUTH_INTERACTIVE` - Enable interactive authentication mode
- `NOTEBOOK` - Target notebook name for testing
