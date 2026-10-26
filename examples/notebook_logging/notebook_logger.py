"""Log Jupyter notebook runs, outputs, and artifacts to LabArchives."""

import html
from datetime import datetime
from io import BytesIO
from mimetypes import guess_type
from pathlib import Path
from secrets import token_urlsafe
from typing import Any

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

try:
    from IPython import get_ipython
except ImportError:
    get_ipython = None


class NotebookLogger:
    """Logs Jupyter notebook runs and outputs to LabArchives."""

    def __init__(
        self,
        notebook_name: str,
        client: Client | None = None,
        user: User | None = None,
    ) -> None:
        """Initialize the logger with Jupyter-friendly auth.

        Displays a clickable auth link in the notebook cell output, then waits
        for the user to authenticate in their browser.

        :param notebook_name: Name of the LabArchives notebook.
        :param client: Optional pre-configured client (loaded from .env if omitted).
        :param user: Optional pre-authenticated User instance.
        """
        self.client = client or Client()
        self.notebook_name = notebook_name
        self.captured_figures: list[bytes] = []
        self._captured_figure_data: dict[int, bytes] = {}
        self.tracked_files: list[str] = []

        self._configure_figure_capture()
        self.user = self._authenticate(user)

    def _configure_figure_capture(self) -> None:
        """Configure IPython/matplotlib hooks to capture rendered figures."""
        ip = get_ipython()
        if not ip:
            return

        try:
            import matplotlib.figure
            import matplotlib.pyplot as plt
        except ImportError:
            return

        def capture_fig(fig):
            return self._serialize_figure(fig)

        ip.display_formatter.formatters["image/png"].for_type(
            matplotlib.figure.Figure, capture_fig
        )

        original_show = plt.show

        def capture_show(*args: Any, **kwargs: Any):
            # Capture currently open figures before inline backends close them.
            for fig_num in plt.get_fignums():
                self._serialize_figure(plt.figure(fig_num))
            return original_show(*args, **kwargs)

        plt.show = capture_show

    def _authenticate(self, user: User | None) -> User:
        """Authenticate the user, reusing an existing session when provided."""
        if user is not None:
            print(f"Using existing authentication for: {user.email}")
            return user

        port = 8089
        callback_path = f"/auth/notebook-logger/{token_urlsafe(12)}/"
        auth_url = self.client.generate_auth_url(
            f"http://127.0.0.1:{port}{callback_path}"
        )

        with self.client.collect_auth_response(
            port=port,
            callback_path=callback_path,
        ) as auth_response_collector:
            self._display_auth_prompt(auth_url)
            print("Waiting for authentication...")
            authenticated_user = auth_response_collector.wait()

        print(f"Authenticated as: {authenticated_user.email}")
        return authenticated_user

    @staticmethod
    def _display_auth_prompt(auth_url: str) -> None:
        """Display authentication instructions in notebook or terminal."""
        try:
            from IPython.display import HTML, display

            display(
                HTML(
                    f"<p><strong>Authenticate:</strong> "
                    f'<a href="{auth_url}" target="_blank">'
                    f"Click here to log in to LabArchives</a></p>"
                )
            )
        except ImportError:
            print(f"Authenticate by visiting:\n  {auth_url}")

    def track_file(self, path: str) -> None:
        """Register a file to be uploaded with the next log() call."""
        abs_path = str(Path(path).resolve())
        if not Path(abs_path).exists():
            print(f"Warning: File {path} not found.")
            return
        if abs_path not in self.tracked_files:
            self.tracked_files.append(abs_path)
            print(f"Tracking file for LabArchives: {path}")

    def _capture_figures(self) -> list[bytes]:
        """Capture all open matplotlib figures as PNG bytes."""
        figures = list(self.captured_figures)
        seen_figure_ids = set(self._captured_figure_data)

        try:
            import matplotlib.pyplot as plt
        except ImportError:
            self.captured_figures.clear()
            self._captured_figure_data.clear()
            return figures

        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            fig_id = id(fig)
            if fig_id in seen_figure_ids:
                continue
            figures.append(self._serialize_figure(fig))
            seen_figure_ids.add(fig_id)

        self.captured_figures.clear()
        self._captured_figure_data.clear()
        return figures

    def _serialize_figure(self, fig: Any) -> bytes:
        """Serialize a matplotlib figure to PNG bytes and cache it once per cycle."""
        figure_id = id(fig)
        cached = self._captured_figure_data.get(figure_id)
        if cached is not None:
            return cached

        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        data = buf.getvalue()
        self.captured_figures.append(data)
        self._captured_figure_data[figure_id] = data
        return data

    def _capture_cell_info(self) -> dict[str, Any]:
        """Capture recent cell sources and execution count from IPython."""
        ip = get_ipython() if get_ipython else None

        if ip is None:
            return {"source": "(not in IPython)", "execution_count": None}

        history = list(ip.history_manager.get_range(output=False))
        return {
            "execution_count": ip.execution_count,
            "recent_cells": [src for _, _, src in history[-5:]],
        }

    def _capture_last_result(self) -> str:
        """Capture the last cell output value from IPython."""
        ip = get_ipython() if get_ipython else None

        if ip is None:
            return "(no result)"

        result = getattr(ip, "last_execution_result", None)
        if result is not None and result.result is not None:
            return repr(result.result)

        out = ip.user_ns.get("Out", {})
        if out:
            return repr(out[max(out.keys())])

        return "(no result)"

    def _collect_file_paths(self, files: list[str] | None) -> list[str]:
        """Combine tracked and explicit files into a de-duplicated path list."""
        combined = [*self.tracked_files, *(files or [])]
        self.tracked_files.clear()

        unique_paths: list[str] = []
        seen: set[str] = set()
        for path in combined:
            abs_path = str(Path(path).resolve())
            if abs_path in seen:
                continue
            seen.add(abs_path)
            unique_paths.append(abs_path)

        return unique_paths

    def log(
        self,
        tags: list[str],
        cell_info: dict[str, Any],
        result: str,
        figures: list[bytes],
        files: list[str] | None = None,
    ) -> None:
        """Save a notebook run to LabArchives.

        :param tags: List of string tags for this run.
        :param cell_info: Dict with 'execution_count' and 'recent_cells'.
        :param result: String repr of the last cell output.
        :param figures: List of PNG bytes, one per matplotlib figure.
        :param files: Optional list of file paths to attach.
        """
        file_paths = self._collect_file_paths(files)
        notebooks = self.user.notebooks
        try:
            notebook = notebooks[self.notebook_name]
        except KeyError:
            available = ", ".join(notebooks.keys())
            raise RuntimeError(
                f"Notebook '{self.notebook_name}' not found. Available: {available}"
            ) from None

        print("Navigating to logging directory...")

        notebook_log_dir = notebook.create(
            NotebookDirectory, "Notebook Log", if_exists=InsertBehavior.Retain
        )
        user_dir = notebook_log_dir.create(
            NotebookDirectory, self.user.email, if_exists=InsertBehavior.Retain
        )

        timestamp = datetime.now().isoformat(timespec="microseconds").replace(":", "-")
        page = user_dir.create(NotebookPage, timestamp)
        entries = page.entries
        tags_html = "".join(
            f'<span style="background: #eee; padding: 2px 5px; margin: 2px; border-radius: 3px;">{html.escape(tag)}</span>'
            for tag in tags
        )
        recent_cells = cell_info.get("recent_cells", [])
        exec_count = cell_info.get("execution_count")
        cells_html = "".join(
            f"<pre style='background:#f5f5f5;padding:6px;margin:4px 0;'>{html.escape(src)}</pre>"
            for src in recent_cells
        )

        print(
            f"Logging to: {self.notebook_name}/Notebook Log/{self.user.email}/{timestamp}"
        )

        entries.create(TextEntry, f"<p><strong>Tags:</strong> {tags_html}</p>")
        entries.create(
            TextEntry,
            f"<p><strong>Cell Info</strong> (execution count: {exec_count})</p>{cells_html}",
        )
        entries.create(PlainTextEntry, result)

        for i, fig_bytes in enumerate(figures, 1):
            attachment = Attachment(
                BytesIO(fig_bytes),
                "image/png",
                f"figure_{i}.png",
                f"Notebook figure {i}",
            )
            entries.create(AttachmentEntry, attachment)

        for path in file_paths:
            path_obj = Path(path)
            if not path_obj.is_file():
                print(f"Warning: Tracked file '{path}' is not a valid file.")
                continue

            with path_obj.open("rb") as f:
                content = f.read()
                mime_type = guess_type(path_obj)[0] or "application/octet-stream"
                filename = path_obj.name
                attachment = Attachment(
                    BytesIO(content),
                    mime_type,
                    filename,
                    f"Attached file: {filename}",
                )
                entries.create(AttachmentEntry, attachment)

        print("Log complete!")

    def show_ui(self) -> None:
        """Display an ipywidgets form for tagging and saving the current run."""
        try:
            import ipywidgets as widgets
            from IPython.display import display
        except ImportError:
            print(
                "ipywidgets is required for show_ui(). Install it with: pip install ipywidgets"
            )
            return

        tag_input = widgets.Text(
            placeholder="comma-separated tags (e.g. baseline, v1.0)",
            description="Tags:",
            layout=widgets.Layout(width="450px"),
        )
        save_btn = widgets.Button(
            description="Save to LabArchives", button_style="primary"
        )
        status = widgets.Output()

        def on_save(_: widgets.Button) -> None:
            with status:
                tags = [t.strip() for t in tag_input.value.split(",") if t.strip()]
                self.log(
                    tags=tags,
                    cell_info=self._capture_cell_info(),
                    result=self._capture_last_result(),
                    figures=self._capture_figures(),
                )

        save_btn.on_click(on_save)
        display(widgets.VBox([tag_input, save_btn, status]))
