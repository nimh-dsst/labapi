"""Notebook Module.

This module defines the :class:`~labapi.tree.notebook.Notebook` class,
representing a LabArchives notebook. It extends :class:`~labapi.tree.mixins.AbstractTreeContainer`
to manage its hierarchical content (directories and pages) and provides
notebook-level operations (renaming, default-notebook status, entry search).
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING, Literal

from typing_extensions import override

from labapi.exceptions import ApiError

from ._export import _backup_tree, _walk_tree, _write_tree
from .mixins import AbstractTreeContainer, HasNameMixin
from .search import EntrySearch

if TYPE_CHECKING:
    from labapi.user import User
    from labapi.util import NotebookInit

    from .collection import Notebooks


class Notebook(AbstractTreeContainer):
    """Represents a LabArchives notebook, acting as the root of a tree structure.

    A notebook is a specialized :class:`~labapi.tree.mixins.AbstractTreeContainer`
    that holds directories and pages.
    """

    def __init__(self, init: NotebookInit, user: User, notebooks: Notebooks):
        """Initialize a notebook.

        :param init: Initial data for the notebook.
        :param user: The authenticated user.
        :param notebooks: The collection of notebooks this notebook belongs to.
        """
        super().__init__("0", init.name, self, self, user)
        self._id = init.id
        self._is_default = init.is_default
        self._notebooks = notebooks

    @property
    @override
    def id(self) -> str:
        """Return the notebook identifier.

        :returns: The notebook's ID.
        """
        return self._id

    @HasNameMixin.name.setter  # type: ignore[attr-defined]
    def name(self, value: str) -> None:
        """Set the notebook name.

        This operation updates the notebook's name in LabArchives via an API call.

        :param value: The new name for the notebook.
        """
        self.user.api_get("notebooks/modify_notebook_info", nbid=self.id, name=value)

        self._name = value

    @property
    def is_default(self) -> bool:
        """Return whether this notebook is the user's default notebook.

        :returns: True if the notebook is the default, False otherwise.
        """
        return self._is_default

    def search(self, query: str, *, page_size: int = 25) -> EntrySearch:
        """Search entries in this notebook.

        Search itself is read-only. The returned pages contain normal entry
        objects, so setting ``entry.content`` still uses the existing entry
        update behavior.

        :param query: LabArchives search query expression.
        :param page_size: Number of entries to request per result page.
        :returns: A lazy iterable over search result pages.
        """
        return EntrySearch(self, query, page_size=page_size)

    def export(
        self,
        destination: str | PathLike[str],
        *,
        source: Literal["auto", "walk", "backup"] = "auto",
        overwrite: bool = False,
    ) -> Path:
        """Export this notebook to a local directory tree.

        Reconstructs the notebook as a folder mirror under ``destination``:
        one directory per folder/page (named ``<order>_<name>``), with each
        page's content written as ordered files (``NN_text.html`` for rich
        text, ``NN_text.txt`` for plain text, ``NN_<filename>`` for
        attachments).

        :param destination: Output directory for the exported tree. Its parent
            directories are created if needed.
        :param source: Where to read the notebook from. ``"walk"`` reads the
            live API tree; ``"backup"`` downloads and unpacks the native backup
            archive (requires the notebook owner's sign-in and the optional
            ``py7zr`` dependency: ``pip install 'labapi[export]'``); ``"auto"``
            uses the backup archive when available and falls back to the walk.
        :param overwrite: When ``destination`` exists and is not empty, raise
            unless ``overwrite`` is ``True``.
        :returns: The path of the export directory.
        """
        backup_error = None
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            if source != "walk":
                try:
                    tree = _backup_tree(self, tmp_path)
                except (ImportError, ApiError) as error:
                    backup_error = error
                else:
                    return _write_tree(tree, destination, overwrite)

            if source != "backup":
                return _write_tree(_walk_tree(self, tmp_path), destination, overwrite)

        raise RuntimeError(
            f"Could not export notebook with source={source!r}"
        ) from backup_error

    def backup(
        self,
        destination: str | PathLike[str],
        *,
        include_attachments: bool = True,
        as_json: bool = False,
    ) -> Path:
        """Download this notebook's native LabArchives backup archive.

        LabArchives returns the backup as a 7-Zip (``.7z``) archive in
        a proprietary format; ``labapi`` saves it verbatim. This format
        may change at any time, but should remain interpretable and restorable
        by LabArchives.

        :param destination: A filesystem path to write the archive to; its
            parent directories are created if needed.
        :param include_attachments: When ``False``, request a backup without
            attachment payloads (the API ``no_attachments`` option).
        :param as_json: When ``True``, request the notebook data in JSON format
            (the API ``json`` option).
        :returns: The :class:`~pathlib.Path` the archive was written to.
        :raises ApiError: If LabArchives rejects the request. Error code
            ``4547`` means the notebook owner must sign in before this action
            can succeed.
        """
        params: dict[str, str] = {}
        if as_json:
            params["json"] = "true"
        if not include_attachments:
            params["no_attachments"] = "true"

        try:
            stream = self.user.client.stream_api_get(
                "notebooks/notebook_backup",
                uid=self.user.id,
                nbid=self.id,
                **params,
            )
        except ApiError as exc:
            if exc.error_code == 4547:
                raise ApiError(
                    "Downloading a notebook backup requires the notebook owner's "
                    "sign-in (LabArchives error 4547). Check the notebook's owner "
                    "in the LabArchives web UI: Notebook Settings > Users.",
                    exc.error_code,
                ) from exc
            raise

        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        with stream, path.open("wb") as file:
            file.writelines(stream)
        return path
