"""Notebook Page Module.

This module defines the :class:`~labapi.tree.page.NotebookPage` class,
representing a page within a LabArchives notebook. It extends
:class:`~labapi.tree.mixins.AbstractTreeNode` and provides access to the
entries contained within the page.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Literal, cast

from typing_extensions import Self, override

from labapi.entry import (
    Attachment,
    Entries,
    Entry,
    UnimplementedEntry,
    UnknownEntry,
    WidgetEntry,
)
from labapi.util import InsertBehavior, extract_etree

from .mixins import AbstractTreeContainer, AbstractTreeNode

if TYPE_CHECKING:
    from labapi.user import User


class NotebookPage(AbstractTreeNode):
    """Represents a single page within a LabArchives notebook.

    A `NotebookPage` is a leaf node in the tree structure and contains
    a collection of :class:`~labapi.entry.entries.base.Entry` objects.
    Entries are accessed through the :attr:`entries` property.
    """

    def __init__(
        self,
        tree_id: str,
        name: str,
        root: AbstractTreeContainer,
        parent: AbstractTreeContainer,
        user: User,
    ):
        """Initialize a notebook page.

        :param tree_id: The unique ID of the page.
        :param name: The name of the page.
        :param root: The root node of the tree (the Notebook).
        :param parent: The parent node of this page (a Directory or Notebook).
        :param user: The authenticated user.
        """
        super().__init__(tree_id, name, root, parent, user)
        self._entries: Entries | None = None

    @property
    @override
    def id(self) -> str:
        """Return the page identifier.

        :returns: The page's ID.
        """
        return super().id

    @property
    def entries(self) -> Entries:
        """Return this page's entries, loading them from the API on first access.

        .. note::
           Slicing on the returned collection provides snapshots.
           Iterators over the collection are also snapshots and are therefore
           insulated from later collection mutations.

        :returns: An :class:`~labapi.entry.collection.Entries` object managing
                  the page's entries.
        """
        if self._entries is None:
            entries: list[Entry[Any]] = []

            entries_tree = self._user.api_get(
                "tree_tools/get_entries_for_page",
                page_tree_id=self.id,
                nbid=self.root.id,
                entry_data=True,
            )

            for entry in entries_tree.iterfind(".//entry"):
                entry_data = extract_etree(
                    entry,
                    {
                        "eid": str,
                        "part-type": str,
                        "attach-file-name": str,
                        "attach-content-type": str,
                        "entry-data": str,
                    },
                )

                part_type = entry_data["part-type"]

                # Cast extracted string values to ensure type checker knows they're not None
                entry_obj = Entry.from_part_type(
                    part_type,
                    cast(str, entry_data["eid"]),
                    cast(str, entry_data["entry-data"]),
                    self._user,
                )

                if isinstance(entry_obj, WidgetEntry):
                    pass
                elif isinstance(entry_obj, UnimplementedEntry):
                    warnings.warn(
                        f"Entry type '{part_type}' (ID: {entry_data['eid']}) is recognized but not "
                        f"implemented in labapi. Wrapping as UnimplementedEntry.",
                        UserWarning,
                        stacklevel=2,
                    )
                elif isinstance(entry_obj, UnknownEntry):
                    warnings.warn(
                        f"Unknown entry type '{part_type}' (ID: {entry_data['eid']}) encountered. "
                        f"Wrapping as UnknownEntry.",
                        RuntimeWarning,
                        stacklevel=2,
                    )

                entries.append(entry_obj)

            self._entries = Entries(entries, self._user, self)

        return self._entries

    @override
    def copy_to(self, destination: AbstractTreeContainer) -> NotebookPage:
        """Copy this page and its entries into ``destination``.

        .. warning::
           This method has known limitations:

           - LabArchives may rename attachment files during copy operations
           - Only certain entry types are fully supported (text, plain text, headers, attachments)
           - Some entry types may fail to copy and will cause errors

        :param destination: The target container to copy the page to.
        :returns: A new instance of the copied page in the destination.

        Attachment handling during copy:

        - attachment payloads are copied by reading and re-uploading the attachment content,
        - attachment resources opened during copy are always released,
        - any per-entry copy failure is reported via warning and that entry is skipped.

        :raises RuntimeWarning: Emitted when an individual entry fails to copy.
        """
        new_page = destination.create(
            NotebookPage, self.name, if_exists=InsertBehavior.Ignore
        )

        for entry in self.entries:
            entry_content: Any | None = None
            try:
                entry_content = entry.content
                # Re-upload behavior is intentional: copy_to creates a new entry on the
                # destination page using the source entry's runtime class and content.
                # For attachments, Entries.create uploads the payload and returns a
                # distinct destination attachment entry; it does not mutate the source
                # entry or preserve source attachment IDs.
                assert entry_content is not None
                new_page.entries.create(cast(Any, entry.__class__), entry_content)
            except Exception as exc:
                warnings.warn(
                    f"Failed to copy entry {entry.id!r} ({entry.content_type!r}) from page "
                    f"{self.id!r} to page {new_page.id!r}: {exc}. This entry was skipped.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            finally:
                if isinstance(entry_content, Attachment):
                    entry_content.close()

        return new_page

    @override
    def is_dir(self) -> Literal[False]:
        """Return ``False`` because pages are leaf nodes.

        :returns: Always False.
        """
        return False

    @override
    def refresh(self) -> Self:
        """Refresh this page by clearing its cached entries.

        This method clears the internal entries cache, forcing the page
        to re-fetch its entries from the LabArchives API on the next access.

        .. note::
           Entry objects obtained before the refresh are not invalidated and
           may be stale.
        """
        # TODO: Properly invalidate all entry objects before clearing
        self._entries = None
        return self
