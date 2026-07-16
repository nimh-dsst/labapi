"""Notebook Module.

This module defines the :class:`~labapi.tree.notebook.Notebook` class,
representing a LabArchives notebook. It extends :class:`~labapi.tree.mixins.AbstractTreeContainer`
to manage its hierarchical content (directories and pages) and provides
notebook-level operations (renaming, default-notebook status, entry search).
"""

from __future__ import annotations

from os import PathLike
from pathlib import Path
from typing import IO, TYPE_CHECKING, cast

from typing_extensions import override

from labapi.exceptions import ApiError

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

    def backup(
        self,
        destination: str | PathLike[str] | IO[bytes],
        *,
        include_attachments: bool = True,
        as_json: bool = False,
    ) -> None:
        """Download this notebook's native LabArchives backup archive.

        Streams the archive produced by the ``notebooks/notebook_backup`` API
        method to ``destination``. LabArchives returns the backup as a 7-Zip
        (``.7z``) archive in a proprietary format; ``labapi`` saves it verbatim
        without interpreting it.

        :param destination: A filesystem path (its parent directories are
            created if needed) or a writable binary file-like object to stream
            the archive into.
        :param include_attachments: When ``False``, request a backup without
            attachment payloads (the API ``no_attachments`` option).
        :param as_json: When ``True``, request the notebook data in JSON format
            (the API ``json`` option).
        :raises ApiError: If LabArchives rejects the request. Error code
            ``4547`` means the account lacks the notebook admin/backup rights
            required for this action.
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
                    "Downloading a notebook backup requires notebook "
                    "admin/backup rights for this account (LabArchives error "
                    "4547).",
                    exc.error_code,
                ) from exc
            raise

        with stream:
            if isinstance(destination, (str, PathLike)):
                path = Path(cast("str | PathLike[str]", destination))
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("wb") as file:
                    for chunk in stream:
                        file.write(chunk)
            else:
                for chunk in stream:
                    destination.write(chunk)
