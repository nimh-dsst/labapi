#!/usr/bin/env python3
"""Log model metadata, metrics, and artifacts to LabArchives."""

import sys
from collections.abc import Sequence
from datetime import datetime
from html import escape
from typing import Any

from labapi import (
    Attachment,
    AttachmentEntry,
    Client,
    InsertBehavior,
    NotebookDirectory,
    NotebookPage,
    TextEntry,
    User,
)


class ModelLogger:
    """Logs model training runs and metadata to LabArchives."""

    def __init__(self, notebook_name: str, user: User):
        """Initialize the logger with an authenticated user.

        :param notebook_name: Name of the LabArchives notebook.
        :param user: Authenticated LabArchives user session.
        """
        self.user = user
        self.notebook_name = notebook_name

    def log(
        self,
        tags: Sequence[str | list[str]],
        metrics: dict[str, Any],
        results: bytes,
        figures: Sequence[bytes],
        commit: str,
    ) -> None:
        """Log model metadata and artifacts to LabArchives.

        :param tags: List of tags for the run.
        :param metrics: Dictionary of performance metrics.
        :param results: Raw results data (bytes).
        :param figures: List of figures (bytes).
        :param commit: Git commit hash.
        """
        notebooks = self.user.notebooks
        try:
            notebook = notebooks[self.notebook_name]
        except KeyError:
            available = ", ".join(notebooks.keys())
            print(f"Error: Notebook '{self.notebook_name}' not found.")
            print(f"Available: {available}")
            sys.exit(1)

        # Build path: Model Log / {email} / {iso8601}
        print("Navigating to logging directory...")
        model_log_dir = notebook.create(
            NotebookDirectory, "Model Log", if_exists=InsertBehavior.Retain
        )
        user_dir = model_log_dir.create(
            NotebookDirectory, self.user.email, if_exists=InsertBehavior.Retain
        )

        timestamp = datetime.now().isoformat(timespec="seconds").replace(":", "-")
        run_dir = user_dir.create(NotebookDirectory, timestamp)

        # Create the log page
        page = run_dir.create(NotebookPage, "Model Run Details")
        entries = page.entries

        print(
            f"Logging to: {self.notebook_name}/Model Log/{self.user.email}/{timestamp}/"
        )

        # 1. Log Commit Hash
        entries.create(
            TextEntry, f"<p><strong>Git Commit:</strong> {escape(commit)}</p>"
        )

        # 2. Log Tags
        # Flatten tags if they are mixed str and list[str]
        flat_tags: list[str] = []
        for tag in tags:
            if isinstance(tag, list):
                flat_tags.extend(tag)
            else:
                flat_tags.append(tag)

        tags_html = "".join(
            [
                f'<span style="background: #eee; padding: 2px 5px; margin: 2px; border-radius: 3px;">{escape(t)}</span>'
                for t in flat_tags
            ]
        )
        entries.create(TextEntry, f"<p><strong>Tags:</strong> {tags_html}</p>")

        # 3. Log Metrics
        entries.create_json_entry(metrics)

        # 4. Log Results
        from io import BytesIO

        results_attachment = Attachment(
            BytesIO(results),
            "application/octet-stream",
            "results.bin",
            "Model prediction results",
        )
        entries.create(AttachmentEntry, results_attachment)

        # 5. Log Figures
        for i, fig_data in enumerate(figures, 1):
            fig_attachment = Attachment(
                BytesIO(fig_data),
                "image/png",  # Assuming PNG, could be parameterized
                f"figure_{i}.png",
                f"Model evaluation figure {i}",
            )
            entries.create(AttachmentEntry, fig_attachment)

        print("Log complete!")


def main() -> None:
    """Run the model logging example."""
    with Client() as client:
        user = client.default_authenticate()
        print(f"Authenticated as: {user.email} (ID: {user.id})")

        logger = ModelLogger(notebook_name="My Research", user=user)
        logger.log(
            tags=["baseline", ["resnet50", "imagenet"], "v1.0"],
            metrics={"f1": 0.88, "accuracy": 0.92, "loss": 0.15},
            results=b"Prediction results data...",
            figures=[b"fake figure 1 content", b"fake figure 2 content"],
            commit="a1b2c3d4e5f67890",
        )


if __name__ == "__main__":
    main()
