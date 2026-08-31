# Contributing

This guide covers the local development workflow for `labapi`: setting up the
project, running tests, enforcing code style, and following the project's type
system conventions.

## Setup

Install the package and its development dependencies with `uv`, then install
both hook types:

```bash
uv sync --all-groups
pre-commit install --hook-type pre-commit --hook-type pre-push
```

## Running Tests

The test suite is split into unit tests and integration tests. Plain `pytest`
deselects integration tests by default.

Run the full suite, including integration tests, with:

```bash
uv run pytest --integration
```

### Unit Tests

Unit tests use `MockClient` to replay pre-recorded API responses, so they run
entirely offline:

```bash
uv run pytest
uv run pytest --no-cov
uv run pytest tests/tree/test_mixins.py
```

### Integration Tests

Integration tests are opt-in and require live API credentials in `.env` or the
environment:

```bash
# Required
ACCESS_KEYID=your_akid
ACCESS_PWD=your_password
API_URL=https://api.labarchives.com

# Required for non-interactive login used by tests/test_integration.py
AUTH_EMAIL=your@email.com
AUTH_KEY=your_auth_key

# Optional: use the browser callback flow instead
# AUTH_INTERACTIVE=true
```

```bash
uv run pytest --integration tests/test_integration.py
```

`Client()` only auto-loads `API_URL`, `ACCESS_KEYID`, and `ACCESS_PWD`;
`AUTH_EMAIL` and `AUTH_KEY` are test-fixture conventions used by the integration
suite.

## Code Style

Ruff handles linting, formatting, and branch-complexity checks. Pyright handles
type checking. After installing both hook types:

- `ruff-check`, `ruff-format`, and `pyright-check` run on `pre-commit`
- `pytest-check` runs `uv run pytest --no-cov` on `pre-push`

Manual equivalents:

```bash
uv run ruff check --fix .   # lint
uv run ruff format .        # format
uv run pyright              # typecheck
uv run radon cc src tests -s -a  # complexity report
uv run pytest --no-cov      # pre-push test gate
```

To check formatting and linting without changing files:

```bash
uv run ruff check .
uv run ruff format --check .
```

## Continuous Integration

GitHub Actions run the project's main quality gates in separate workflows:

- unit tests
- lint
- formatting
- type checking
- documentation builds
- manually triggered integration tests

Run the corresponding commands locally before pushing to catch failures before
CI.

## Type System

Run type checking locally with:

```bash
uv run pyright
```

All new code must be fully type-annotated. Key conventions:

- `from __future__ import annotations` in modules that rely on forward references
- `override` on all method overrides
- `TYPE_CHECKING` guards to avoid circular imports
- Generics where they give callers concrete return types (e.g. `Entry[Attachment]`)
- `overload` on APIs such as `__getitem__` that return different types for
  different index kinds

The project targets Python 3.10 and newer. Keep source syntax compatible with
Python 3.10, using `typing_extensions` where needed. For example, use
`TypeVar` and `Generic` rather than PEP 695 generic parameter syntax.
