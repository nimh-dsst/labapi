"""Notebook Collection Module.

This module defines the :class:`~labapi.tree.collection.Notebooks` class,
which acts as a collection manager for a user's LabArchives notebooks.
It provides methods for accessing, iterating over, and creating notebooks.
"""

from __future__ import annotations

from collections.abc import ItemsView, Iterator, KeysView, Mapping, Sequence, ValuesView
from typing import TYPE_CHECKING, Literal, overload

from typing_extensions import override

from labapi.exceptions import ApiError
from labapi.util import IdOrNameIndex, Index, NotebookInit, extract_etree

from .notebook import Notebook

if TYPE_CHECKING:
    from labapi.user import User


class Notebooks(Mapping[IdOrNameIndex, Notebook | Sequence[Notebook]]):
    """A collection of LabArchives notebooks accessible to a user.

    This class provides dictionary-like access to notebooks by their ID or name,
    and supports creating new notebooks. It manages a list of :class:`~labapi.tree.notebook.Notebook`
    objects.
    """

    def __init__(self, notebooks: Sequence[NotebookInit], user: User):
        """Initialize the notebook collection.

        :param notebooks: A sequence of :class:`~labapi.util.types.NotebookInit` objects
                          containing initial data for the notebooks.
        :param user: The authenticated :class:`~labapi.user.User` associated with these notebooks.
        """
        super().__init__()
        self._user = user
        self._notebooks = [Notebook(n, user, self) for n in notebooks]
        self._notebooks_by_id = {n.id: n for n in self._notebooks}

    @overload
    def __getitem__(self, key: str) -> Notebook: ...

    @overload
    def __getitem__(self, key: slice[Literal[Index.Id], str, None]) -> Notebook: ...

    @overload
    def __getitem__(
        self, key: slice[Literal[Index.Name], str, None]
    ) -> list[Notebook]: ...

    @override
    def __getitem__(self, key: IdOrNameIndex) -> Notebook | list[Notebook]:
        """Look up notebooks by name or indexed selector.

        - If `key` is a string, it attempts to find a single notebook with that name.
        - If `key` is a slice with start of :attr:`~labapi.util.Index.Id`
          (e.g., ``Index.Id:"some_id"``),
          it returns the notebook with the matching ID.
        - If `key` is a slice with start of :attr:`~labapi.util.Index.Name`
          (e.g., ``Index.Name:"some_name"``),
          it returns a list of all notebooks with the matching name (as names are not unique).

        :param key: The index to use for accessing notebooks. Can be a string (for name lookup),
                    or a slice with :attr:`~labapi.util.Index.Id` or
                    :attr:`~labapi.util.Index.Name`.
        :returns: A single :class:`~labapi.tree.notebook.Notebook` object or a list of them.
        :raises KeyError: If a single notebook is requested by ID or unique name and not found.
        """
        match key:
            case slice(start=Index.Id, stop=val):
                return self._notebooks_by_id[val]
            case slice(start=Index.Name, stop=val):
                return [node for node in self._notebooks if node.name == val]
            case str():
                for node in self._notebooks:
                    if node.name == key:
                        return node
                raise KeyError(f'Notebook with name "{key}" not found')
            case _:
                raise TypeError(
                    "Invalid key type. Use `str`, `Index.Id:<id>`, or `Index.Name:<name>`."
                )

    @override
    def __iter__(self) -> Iterator[str]:
        """Iterate over notebook names in collection order."""
        return iter([c.name for c in self._notebooks])

    def __reversed__(self) -> Iterator[str]:
        """Iterate over notebook names in reverse collection order."""
        return reversed([c.name for c in self._notebooks])

    @override
    def __len__(self) -> int:
        """Return the number of notebooks in this collection."""
        return len(self._notebooks)

    def _mapping_view_dict(self) -> dict[str, Notebook]:
        d: dict[str, Notebook] = {}
        for n in self._notebooks:
            if n.name not in d:
                d[n.name] = n
        return d

    @override
    def keys(self) -> KeysView[str]:
        """Return a mapping-compatible view of notebook names.

        :returns: A keys view of notebook names.
        """
        return KeysView(self._mapping_view_dict())

    @override
    def items(self) -> ItemsView[str, Notebook]:
        """Return a mapping-compatible view of ``(name, notebook)`` pairs.

        :returns: An items view of ``(name, notebook)`` pairs.
        """
        return ItemsView(self._mapping_view_dict())

    @override
    def values(self) -> ValuesView[Notebook]:
        """Return a mapping-compatible view of notebook objects.

        :returns: A values view of notebook objects.
        """
        return ValuesView(self._mapping_view_dict())

    def all_keys(self) -> Sequence[str]:
        """Return notebook names in collection order, preserving duplicates."""
        return [n.name for n in self._notebooks]

    def all_items(self) -> Sequence[tuple[str, Notebook]]:
        """Return ``(name, notebook)`` pairs in collection order, preserving duplicates."""
        return [(n.name, n) for n in self._notebooks]

    def all_values(self) -> Sequence[Notebook]:
        """Return notebook objects in collection order, preserving duplicates."""
        return list(self._notebooks)

    def create_notebook(self, name: str) -> Notebook:
        """Create a new notebook in LabArchives.

        :param name: The name of the new notebook.
        :returns: The newly created :class:`~labapi.tree.notebook.Notebook` object.
        :raises RuntimeError: If the underlying client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns a non-success response, or if
                          the API returns a notebook ID that already exists in
                          the local collection.
        """
        nbid = extract_etree(
            self._user.api_get(
                "notebooks/create_notebook", name=name, initial_folders="Empty"
            ),
            {"nbid": str},
        )["nbid"]

        if nbid in self._notebooks_by_id:
            raise ApiError(f"API returned an existing notebook ID: {nbid}")

        new_notebook = Notebook(NotebookInit(nbid, name, False), self._user, self)

        self._notebooks.append(new_notebook)
        self._notebooks_by_id[nbid] = new_notebook

        return new_notebook
