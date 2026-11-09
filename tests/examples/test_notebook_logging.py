"""Tests for the notebook_logging example script."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from types import ModuleType, SimpleNamespace, TracebackType
from typing import Any, Self, cast

import pytest

from labapi import (
    Attachment,
    AttachmentEntry,
    Client,
    InsertBehavior,
    NotebookDirectory,
    NotebookPage,
    PlainTextEntry,
    TextEntry,
    User,
)

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "examples" / "notebook_logging"
EMAIL = "researcher@example.com"


def _load_example_module(module_name: str, filename: str):
    """Load an example module from the notebook_logging example directory."""
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


notebook_logger = _load_example_module("notebook_logger", "notebook_logger.py")


class _EntriesDouble:
    """Record entry creation calls in order."""

    def __init__(self) -> None:
        """Initialize the capture buffer."""
        self.created: list[tuple[type, Any]] = []

    def create(self, cls: type, data: Any, **_kwargs: Any) -> object:
        """Record a created entry and return a placeholder."""
        if isinstance(data, Attachment):
            # Read eagerly: the example builds attachments from short-lived buffers.
            data = (data.filename, data.mime_type, data.caption, data.read())
        self.created.append((cls, data))
        return object()


class _PageDouble:
    """Minimal page double exposing an entries collection."""

    def __init__(self, name: str) -> None:
        """Initialize the page double."""
        self.name = name
        self.entries = _EntriesDouble()


class _DirDouble:
    """Container double that records directory and page creation."""

    def __init__(self, name: str) -> None:
        """Initialize an empty container."""
        self.name = name
        self.dirs: dict[str, _DirDouble] = {}
        self.pages: list[_PageDouble] = []
        self.create_calls: list[tuple[type, str, Any]] = []

    def create(self, cls: type, name: str, if_exists: Any = None) -> Any:
        """Create (or retain) a child directory, or create a new page."""
        self.create_calls.append((cls, name, if_exists))
        if cls is NotebookPage:
            page = _PageDouble(name)
            self.pages.append(page)
            return page
        if name in self.dirs and if_exists is InsertBehavior.Retain:
            return self.dirs[name]
        child = _DirDouble(name)
        self.dirs[name] = child
        return child


class _UserDouble:
    """Minimal user double exposing notebooks and an email."""

    def __init__(self, notebook: _DirDouble) -> None:
        """Initialize the user double with one notebook."""
        self.notebooks = {"My Notebook": notebook}
        self.email = EMAIL


class _FormatterDouble:
    """Record IPython display-formatter registrations."""

    def __init__(self) -> None:
        """Initialize the registration buffer."""
        self.registered: list[type] = []

    def for_type(self, typ: type, _func: Callable[[Any], Any]) -> None:
        """Record a type registration."""
        self.registered.append(typ)


class _HistoryDouble:
    """Minimal IPython history manager double."""

    def __init__(self, sources: list[str]) -> None:
        """Initialize with executed cell sources."""
        self._sources = sources

    def get_range(self, output: bool = False) -> Iterator[tuple[int, int, str]]:
        """Yield (session, line, source) tuples like IPython does."""
        del output
        for line, source in enumerate(self._sources, 1):
            yield 1, line, source


class _ShellDouble:
    """Minimal IPython shell double used by the logger's capture helpers."""

    def __init__(self, sources: list[str], last_result: Any) -> None:
        """Initialize the shell double."""
        self.display_formatter = SimpleNamespace(
            formatters={"image/png": _FormatterDouble()}
        )
        self.history_manager = _HistoryDouble(sources)
        self.execution_count = len(sources)
        self.last_execution_result = SimpleNamespace(result=last_result)
        self.user_ns: dict[str, Any] = {}


class _ButtonDouble:
    """ipywidgets.Button double that can be clicked from a test."""

    def __init__(self, **_kwargs: Any) -> None:
        """Initialize without a click handler."""
        self._handler: Callable[[Any], None] | None = None

    def on_click(self, handler: Callable[[Any], None]) -> None:
        """Register the click handler."""
        self._handler = handler

    def click(self) -> None:
        """Invoke the registered click handler."""
        assert self._handler is not None
        self._handler(self)


class _OutputDouble:
    """ipywidgets.Output double usable as a context manager."""

    def __init__(self, **_kwargs: Any) -> None:
        """Initialize the output double."""

    def __enter__(self) -> Self:
        """Enter the output capture context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Leave the output capture context without suppressing errors."""


class _WidgetsUI:
    """Fake ipywidgets/IPython.display modules that expose created widgets."""

    def __init__(self) -> None:
        """Build the fake modules."""
        self.texts: list[SimpleNamespace] = []
        self.buttons: list[_ButtonDouble] = []
        self.displayed: list[Any] = []

        widgets = ModuleType("ipywidgets")
        widgets.__dict__.update(
            Text=self._make_text,
            Button=self._make_button,
            Output=_OutputDouble,
            Layout=lambda **kwargs: SimpleNamespace(**kwargs),
            VBox=lambda children: SimpleNamespace(children=children),
        )
        display_module = ModuleType("IPython.display")
        display_module.__dict__.update(display=self.displayed.append)
        ipython = ModuleType("IPython")
        ipython.__dict__.update(display=display_module)
        self.modules = {
            "ipywidgets": widgets,
            "IPython": ipython,
            "IPython.display": display_module,
        }

    def _make_text(self, **kwargs: Any) -> SimpleNamespace:
        """Create a text widget double with an empty value."""
        text = SimpleNamespace(value="", **kwargs)
        self.texts.append(text)
        return text

    def _make_button(self, **kwargs: Any) -> _ButtonDouble:
        """Create a button widget double."""
        button = _ButtonDouble(**kwargs)
        self.buttons.append(button)
        return button


class _CollectorDouble:
    """Auth response collector double returning a preset user."""

    def __init__(self, user: _UserDouble) -> None:
        """Initialize with the user to return."""
        self._user = user

    def __enter__(self) -> Self:
        """Enter the collector context."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Leave the collector context."""

    def wait(self) -> _UserDouble:
        """Return the authenticated user."""
        return self._user


class _ClientDouble:
    """Client double recording the auth callback flow."""

    def __init__(self, user: _UserDouble) -> None:
        """Initialize with the user the callback will yield."""
        self._user = user
        self.redirect_urls: list[str] = []
        self.collector_args: list[tuple[int, str]] = []

    def generate_auth_url(self, redirect_url: str) -> str:
        """Record the redirect URL and return a fake auth URL."""
        self.redirect_urls.append(redirect_url)
        return "https://example.invalid/auth"

    def collect_auth_response(
        self, *, port: int, callback_path: str
    ) -> _CollectorDouble:
        """Record collector arguments and return the collector double."""
        self.collector_args.append((port, callback_path))
        return _CollectorDouble(self._user)


@pytest.fixture
def no_ipython(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the logger as if IPython were not installed (the import fallback)."""
    monkeypatch.setattr(notebook_logger, "get_ipython", None)


def _make_logger(notebook: _DirDouble) -> Any:
    """Create a NotebookLogger with a pre-authenticated user double."""
    return notebook_logger.NotebookLogger(
        "My Notebook",
        client=cast(Client, object()),
        user=cast(User, _UserDouble(notebook)),
    )


def test_show_ui_save_logs_run_to_new_user_page(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """Clicking Save writes tags, cell info, result and tracked files to a new page."""
    shell = _ShellDouble(["x = 1", "print('<hi>')", "x + 1"], last_result=2)
    monkeypatch.setattr(notebook_logger, "get_ipython", lambda: shell)
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        pass
    else:
        # The logger replaces plt.show(); restore it after the test.
        monkeypatch.setattr(plt, "show", plt.show)
        plt.close("all")
    ui = _WidgetsUI()
    for name, module in ui.modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    results_file = tmp_path / "results.txt"
    results_file.write_bytes(b"a,b\n1,2\n")
    notebook = _DirDouble("My Notebook")
    logger = _make_logger(notebook)
    logger.track_file(str(results_file))

    logger.show_ui()
    (tag_input,) = ui.texts
    (save_button,) = ui.buttons
    tag_input.value = "baseline, <v1>, "
    save_button.click()

    assert notebook.create_calls == [
        (NotebookDirectory, "Notebook Log", InsertBehavior.Retain)
    ]
    log_dir = notebook.dirs["Notebook Log"]
    assert log_dir.create_calls == [(NotebookDirectory, EMAIL, InsertBehavior.Retain)]
    (page,) = log_dir.dirs[EMAIL].pages
    assert ":" not in page.name

    created = page.entries.created
    assert [cls for cls, _ in created] == [
        TextEntry,
        TextEntry,
        PlainTextEntry,
        AttachmentEntry,
    ]
    tags_html = created[0][1]
    assert ">baseline</span>" in tags_html
    assert ">&lt;v1&gt;</span>" in tags_html
    assert tags_html.count("<span") == 2
    cell_html = created[1][1]
    assert "(execution count: 3)" in cell_html
    assert "print(&#x27;&lt;hi&gt;&#x27;)" in cell_html
    assert created[2][1] == "2"
    assert created[3][1] == (
        "results.txt",
        "text/plain",
        "Attached file: results.txt",
        b"a,b\n1,2\n",
    )
    assert logger.tracked_files == []


def test_log_attaches_open_matplotlib_figures(no_ipython: None):
    """Open matplotlib figures are captured and attached as numbered PNGs."""
    del no_ipython
    pytest.importorskip("matplotlib")
    import matplotlib.pyplot as plt

    plt.switch_backend("Agg")
    plt.close("all")
    notebook = _DirDouble("My Notebook")
    logger = _make_logger(notebook)
    fig = plt.figure()
    fig.add_subplot().plot([0, 1], [1, 0])
    try:
        logger.log(
            tags=[],
            cell_info=logger._capture_cell_info(),
            result=logger._capture_last_result(),
            figures=logger._capture_figures(),
        )
    finally:
        plt.close("all")

    (page,) = notebook.dirs["Notebook Log"].dirs[EMAIL].pages
    created = page.entries.created
    assert [cls for cls, _ in created] == [
        TextEntry,
        TextEntry,
        PlainTextEntry,
        AttachmentEntry,
    ]
    assert created[2][1] == "(no result)"
    filename, mime_type, caption, content = created[3][1]
    assert (filename, mime_type, caption) == (
        "figure_1.png",
        "image/png",
        "Notebook figure 1",
    )
    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    assert logger._capture_figures() == []


def test_repeated_logs_reuse_directories_and_add_pages(no_ipython: None):
    """Each log() call adds a new page under the same retained user directory."""
    del no_ipython
    notebook = _DirDouble("My Notebook")
    logger = _make_logger(notebook)

    for tag in ("first", "second"):
        logger.log(tags=[tag], cell_info={}, result="r", figures=[])

    assert list(notebook.dirs) == ["Notebook Log"]
    user_dir = notebook.dirs["Notebook Log"].dirs[EMAIL]
    assert len(user_dir.pages) == 2


def test_log_reports_available_notebooks_when_missing(no_ipython: None):
    """An unknown notebook name raises without creating anything."""
    del no_ipython
    notebook = _DirDouble("My Notebook")
    logger = notebook_logger.NotebookLogger(
        "Missing",
        client=cast(Client, object()),
        user=cast(User, _UserDouble(notebook)),
    )

    with pytest.raises(RuntimeError, match="Available: My Notebook"):
        logger.log(tags=[], cell_info={}, result="", figures=[])

    assert notebook.create_calls == []


def test_init_without_user_authenticates_through_local_callback(no_ipython: None):
    """Without a user, the logger runs the local-callback auth flow."""
    del no_ipython
    user = _UserDouble(_DirDouble("My Notebook"))
    client = _ClientDouble(user)

    logger = notebook_logger.NotebookLogger("My Notebook", client=cast(Client, client))

    assert logger.user is user
    ((port, callback_path),) = client.collector_args
    assert port == 8089
    assert client.redirect_urls == [f"http://127.0.0.1:{port}{callback_path}"]
