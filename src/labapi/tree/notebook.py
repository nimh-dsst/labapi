"""Notebook Module.

This module defines the :class:`~labapi.tree.notebook.Notebook` class,
representing a LabArchives notebook. It extends :class:`~labapi.tree.mixins.AbstractTreeContainer`
to manage its hierarchical content (directories and pages) and provides
notebook-level operations (renaming, default-notebook status, entry search).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

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
