"""Tests for the model_logging example script."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, cast

from labapi import NotebookPage, TextEntry, User

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "model_logging"


def _load_example_module(module_name: str, filename: str):
    """Load an example module from the model_logging example directory."""
    module_path = EXAMPLE_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    sys.path.insert(0, str(EXAMPLE_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


model_logger = _load_example_module("model_logger", "model_logger.py")


class _EntriesDouble:
    """Capture entry creation calls without hitting the API."""

    def __init__(self) -> None:
        """Initialize capture buffers."""
        self.text_html: list[str] = []
        self.json_calls: list[Any] = []
        self.attachments: list[Any] = []

    def create(self, cls: type, data: Any, **_kwargs: Any) -> object:
        """Record a created entry, splitting text HTML from attachments."""
        if cls is TextEntry:
            self.text_html.append(cast(str, data))
        else:
            self.attachments.append(data)
        return object()

    def create_json_entry(self, metrics: Any, **_kwargs: Any) -> tuple[object, object]:
        """Record a JSON entry creation."""
        self.json_calls.append(metrics)
        return object(), object()


class _PageDouble:
    """Minimal page double exposing an entries collection."""

    def __init__(self, entries: _EntriesDouble) -> None:
        """Initialize the page double."""
        self.entries = entries


class _DirDouble:
    """Minimal container double that creates nested dirs and a page."""

    def __init__(self, page: _PageDouble) -> None:
        """Initialize the container double."""
        self._page = page

    def create(self, cls: type, _name: str, if_exists: Any = None) -> Any:
        """Return the page for NotebookPage, otherwise another directory."""
        del if_exists
        if cls is NotebookPage:
            return self._page
        return self


class _UserDouble:
    """Minimal user double exposing notebooks and an email."""

    def __init__(self, notebook: _DirDouble) -> None:
        """Initialize the user double with one notebook."""
        self.notebooks = {"My Research": notebook}
        self.email = "researcher@example.com"


def test_log_escapes_commit_and_tags():
    """User-supplied commit and tags are HTML-escaped before embedding in HTML."""
    entries = _EntriesDouble()
    user = _UserDouble(_DirDouble(_PageDouble(entries)))
    logger = model_logger.ModelLogger("My Research", cast(User, user))

    logger.log(
        tags=["<img src=x onerror=alert(1)>"],
        metrics={},
        results=b"",
        figures=[],
        commit="<b>x</b>",
    )

    commit_html, tags_html = entries.text_html[0], entries.text_html[1]

    assert "<b>x</b>" not in commit_html
    assert "&lt;b&gt;x&lt;/b&gt;" in commit_html
    assert "<img" not in tags_html
    assert "&lt;img" in tags_html


def test_log_success_message_is_ascii_safe(capsys):
    """log() output must be printable on a non-UTF-8 (e.g. cp1252) console."""
    entries = _EntriesDouble()
    user = _UserDouble(_DirDouble(_PageDouble(entries)))
    logger = model_logger.ModelLogger("My Research", cast(User, user))

    logger.log(tags=[], metrics={}, results=b"", figures=[], commit="abc123")

    out = capsys.readouterr().out
    assert "Log complete!" in out
    # Would raise UnicodeEncodeError if any character (e.g. a checkmark) is not
    # encodable in the default Windows console encoding.
    out.encode("cp1252")
