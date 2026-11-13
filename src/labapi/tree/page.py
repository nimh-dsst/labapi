"""Notebook Page Module.

This module defines the :class:`~labapi.tree.page.NotebookPage` class,
representing a page within a LabArchives notebook. It extends
:class:`~labapi.tree.mixins.AbstractTreeNode` and provides access to the
entries contained within the page.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Literal, Self, cast

from typing_extensions import override

from labapi.entry import (
    Attachment,
    AttachmentEntry,
    Entries,
    Entry,
    UnimplementedEntry,
    UnknownEntry,
    WidgetEntry,
)
from labapi.util import InsertBehavior, extract_etree, to_datetime

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
    def url(self) -> str:
        """Return this page's LabArchives Web UI URL."""
        return f"{self.user.client.web_url}/{self.root.id}/page/{self.id}"

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
                entry_fields = extract_etree(
                    entry,
                    {
                        "eid": str,
                        "part-type": str,
                    },
                )
                entry_optional = extract_etree(
                    entry,
                    {
                        "entry-data": str,
                        "caption": str,
                        "attach-file-name": str,
                        "created-at": to_datetime,
                        "updated-at": to_datetime,
                        "version": int,
                    },
                    raise_missing=False,
                )

                part_type = entry_fields["part-type"]
                data = (
                    entry_optional.get("entry-data")
                    or entry_optional.get("caption")
                    or ""
                )
                # Cast extracted string values to ensure type checker knows they're not None
                entry_obj = Entry.from_part_type(
                    part_type,
                    cast(str, entry_fields["eid"]),
                    data,
                    self._user,
                    created_at=entry_optional.get("created-at"),
                    updated_at=entry_optional.get("updated-at"),
                    version=entry_optional.get("version"),
                )

                if isinstance(entry_obj, AttachmentEntry):
                    entry_obj._filename = entry_optional.get("attach-file-name") or None  # pyright: ignore[reportPrivateUsage]

                if isinstance(entry_obj, WidgetEntry):
                    pass
                elif isinstance(entry_obj, UnimplementedEntry):
                    warnings.warn(
                        f"Entry type '{part_type}' (ID: {entry_fields['eid']}) is recognized but not "
                        f"implemented in labapi. Wrapping as UnimplementedEntry.",
                        UserWarning,
                        stacklevel=2,
                    )
                elif isinstance(entry_obj, UnknownEntry):
                    warnings.warn(
                        f"Unknown entry type '{part_type}' (ID: {entry_fields['eid']}) encountered. "
                        f"Wrapping as UnknownEntry.",
                        RuntimeWarning,
                        stacklevel=2,
                    )

                entries.append(entry_obj)

            self._entries = Entries(entries, self._user, self)

        return self._entries

    @override
    def copy_to(
        self, destination: AbstractTreeContainer, *, strict: bool = False
    ) -> NotebookPage:
        """Copy this page and its entries into ``destination``.

        .. warning::
           This method has known limitations:

           - LabArchives may rename attachment files during copy operations
           - Only certain entry types are fully supported (text, plain text, headers, attachments)
           - Some entry types may fail to copy and will cause errors

        :param destination: The target container to copy the page to.
        :param strict: If ``True``, any entry that fails to copy aborts the whole
            copy (and triggers the rollback below) instead of being warned about
            and skipped.
        :returns: A new instance of the copied page in the destination.

        Attachment handling during copy:

        - attachment payloads are copied by reading and re-uploading the attachment content,
        - attachment resources opened during copy are always released,
        - by default, any per-entry copy failure is reported via warning and that entry is skipped.

        .. note::
           By default (``strict=False``), a per-entry copy failure emits a
           :class:`RuntimeWarning` (it is *not* raised as an exception) and the
           entry is skipped, so a partial copy does not abort. To detect skipped
           entries, capture warnings with ``warnings.catch_warnings(record=True)``,
           or pass ``strict=True`` to turn such failures into an aborted copy.

        Failure handling: if the copy aborts (e.g. the source entries cannot be
        loaded, or, with ``strict=True``, any entry fails), the page created here is
        moved to *API Deleted Items* before the error is re-raised (the public API
        has no hard delete), so the destination no longer contains it.

        Emits :class:`RuntimeWarning` if the rollback itself fails; the original
        error is still raised.
        """
        new_page = destination.create(
            NotebookPage, self.name, if_exists=InsertBehavior.Ignore
        )

        try:
            for entry in self.entries:
                entry_content: Any | None = None
                try:
                    entry_content = entry.content
                    # Re-upload behavior is intentional: copy_to creates a new entry on the
                    # destination page using the source entry's runtime class and content.
                    # For attachments, Entries.create uploads the payload and returns a
                    # distinct destination attachment entry; it does not mutate the source
                    # entry or preserve source attachment IDs.
                    if entry_content is None:
                        raise ValueError(
                            f"Entry {entry.id!r} ({entry.content_type!r}) has no "
                            "content to copy"
                        )
                    new_page.entries.create(cast(Any, entry.__class__), entry_content)
                # Intentionally broad: by default copy_to skips an entry it cannot copy
                # and warns, so one failure does not abort the whole copy; strict=True
                # re-raises instead. Narrow if a specific type becomes known.
                except Exception as exc:
                    if strict:
                        raise
                    warnings.warn(
                        f"Failed to copy entry {entry.id!r} ({entry.content_type!r}) from page "
                        f"{self.id!r} to page {new_page.id!r}: {exc}. This entry was skipped.",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                finally:
                    if isinstance(entry_content, Attachment):
                        entry_content.close()
        except Exception:
            new_page._discard_partial_copy()
            raise

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
