"""Entries collection class."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime, timezone
from html import escape
from io import BytesIO
from json import dumps
from typing import TYPE_CHECKING, Any, SupportsIndex, TypeVar, cast, overload

from typing_extensions import override

from labapi.util import extract_etree

from .attachment import Attachment
from .entries import (
    AttachmentEntry,
    Entry,
    PlainTextEntry,
    TextEntry,
    UnknownEntry,
)

E = TypeVar("E", bound="Entry[Any]")

if TYPE_CHECKING:
    from labapi.tree import NotebookPage
    from labapi.user import User
    from labapi.util import JsonData


class Entries(Sequence["Entry[Any]"]):
    """A collection of entries on a LabArchives page.

    This class provides a sequence-like interface for managing entries within
    a page, including a generic method for creating new entries by class.
    """

    def __init__(self, entries: Sequence[Entry[Any]], user: User, page: NotebookPage):
        """Initialize an entries collection.

        :param entries: A sequence of
                        :class:`~labapi.entry.entries.base.Entry` objects.
        :param user: The authenticated user.
        :param page: The page that this collection belongs to.
        """
        super().__init__()
        self._user = user
        self._page = page
        self._entries: list[Entry[Any]] = list(entries)

    @overload
    def __getitem__(self, index: SupportsIndex) -> Entry[Any]:
        pass

    @overload
    def __getitem__(self, index: str) -> Entry[Any]:
        pass

    @overload
    def __getitem__(self, index: slice) -> Sequence[Entry[Any]]:
        pass

    @override
    def __getitem__(
        self, index: SupportsIndex | str | slice[Any, Any, Any]
    ) -> Entry[Any] | Sequence[Entry[Any]]:
        """Look up entries by index, slice, or entry identifier."""
        if isinstance(index, str):
            for entry in self._entries:
                if entry.id == index:
                    return entry
            raise KeyError(f"Entry with id '{index}' not found")
        return self._entries[index]

    @override
    def __iter__(self) -> Iterator[Entry[Any]]:
        """Iterate over a snapshot of this page's entries."""
        return iter(tuple(self._entries))

    @override
    def __reversed__(self) -> Iterator[Entry[Any]]:
        """Iterate over a snapshot of this page's entries in reverse order."""
        return reversed(tuple(self._entries))

    @override
    def __len__(self):
        """Return the number of entries in this collection."""
        return len(self._entries)

    def get_by_id(self, entry_id: str) -> Entry[Any]:
        """Return the entry with the given ID.

        This is a readable equivalent of ``entries[entry_id]``.

        :param entry_id: The ID of the entry to retrieve.
        :returns: The single :class:`~labapi.entry.entries.base.Entry` with the
                  matching ID.
        :raises KeyError: If no entry has the given ID.
        """
        return self[entry_id]

    def of_type(self, cls: type[E]) -> list[E]:
        """Return all entries that are instances of ``cls``.

        Filtering uses :func:`isinstance`, so passing a base class also matches
        its subclasses (for example, ``of_type(PlainTextEntry)`` matches
        :class:`~labapi.entry.entries.text.TextEntry` and
        :class:`~labapi.entry.entries.text.HeaderEntry` as well).

        :param cls: The entry class to filter by.
        :returns: A list of entries of the requested type, in collection order;
                  empty if none match.
        """
        return [cast(E, entry) for entry in self._entries if isinstance(entry, cls)]

    def attachments(self) -> list[AttachmentEntry]:
        """Return all attachment entries in this collection.

        Convenience wrapper for ``of_type(AttachmentEntry)``.

        :returns: A list of
                  :class:`~labapi.entry.entries.attachment.AttachmentEntry`
                  objects, in collection order; empty if none match.
        """
        return self.of_type(AttachmentEntry)

    def texts(self) -> list[PlainTextEntry]:
        """Return all text-content entries in this collection.

        Convenience wrapper for ``of_type(PlainTextEntry)``. Because
        :class:`~labapi.entry.entries.text.PlainTextEntry` is the base class for
        string-content entries, this includes plain text, rich text
        (:class:`~labapi.entry.entries.text.TextEntry`), and heading
        (:class:`~labapi.entry.entries.text.HeaderEntry`) entries. Use
        :meth:`of_type` with a specific class for a narrower filter.

        :returns: A list of
                  :class:`~labapi.entry.entries.text.PlainTextEntry` objects (and
                  subclasses), in collection order; empty if none match.
        """
        return self.of_type(PlainTextEntry)

    # TODO delete entries

    def create_json_entry(
        self,
        data: JsonData,
        *,
        filename: str | None = None,
        caption: str | None = None,
    ) -> tuple[AttachmentEntry, TextEntry]:
        """Create a JSON attachment plus a companion reference text entry.

        The companion text entry references the attachment's ID and displays a
        formatted preview of the JSON data.

        :param data: The JSON-serializable data to upload.
        :param filename: Optional stable filename for the uploaded JSON attachment.
        :param caption: Optional label/caption for the generated attachment and reference entry.
        :returns: A tuple containing the attachment entry and the text entry.
        """
        # TODO treat this as one entry in the code

        name = (
            filename
            or f"uploaded_data_{datetime.now(timezone.utc).timestamp():.0f}.json"
        )
        display_caption = caption or name
        preview_json = escape(dumps(data, indent=4))

        file_entry = self.create(
            AttachmentEntry,
            Attachment(
                BytesIO(dumps(data).encode()),
                "application/json",
                name,
                display_caption,
            ),
        )

        try:
            text_entry = self.create(
                TextEntry,
                f"""
<p>Reference Attachment: {escape(display_caption)}</p>
<p>Entry ID: {escape(file_entry.id)}</p>
<pre>
{preview_json}
</pre>
""",
            )
        except Exception as e:
            from labapi.exceptions import PartialEntryCreateError

            raise PartialEntryCreateError(
                f"Failed to create companion text entry for attachment {file_entry.id}",
                partial_entry=file_entry,
            ) from e
        return file_entry, text_entry

    @overload
    def create(
        self,
        cls: type[AttachmentEntry],
        data: Attachment,
        *,
        client_ip: str | None = None,
    ) -> AttachmentEntry: ...

    @overload
    def create(self, cls: type[E], data: str, *, client_ip: str | None = None) -> E: ...

    def create(
        self, cls: type[E], data: str | Attachment, *, client_ip: str | None = None
    ) -> E:
        """Create a new entry on the page.

        This method supports creating any entry type by passing the entry class directly,
        similar to :meth:`~labapi.tree.mixins.AbstractTreeContainer.create`. The created
        entry is automatically added to the collection.

        :param cls: The entry class to create (e.g.,
                    :class:`~labapi.entry.entries.text.TextEntry`,
                    :class:`~labapi.entry.entries.text.HeaderEntry`, or
                    :class:`~labapi.entry.entries.attachment.AttachmentEntry`).
        :param data: The content of the entry. For text-based entries, this should be a string.
                    For
                    :class:`~labapi.entry.entries.attachment.AttachmentEntry`,
                    this should be an
                    :class:`~labapi.entry.attachment.Attachment` object.
        :param client_ip: Optional end-user IP to pass through on attachment uploads.
        :returns: The newly created entry object of the specified type.
        :raises TypeError: If ``data`` does not match the entry class being
                           created.
        :raises RuntimeError: If the underlying client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.

        Invalid XML propagates ``lxml.etree.XMLSyntaxError``.
        """
        if issubclass(cls, UnknownEntry):
            raise TypeError(f"{cls.__name__} cannot be created")

        if issubclass(cls, AttachmentEntry):
            if not isinstance(data, Attachment):
                raise TypeError(
                    f"{cls.__name__} requires Attachment data, got "
                    f"{type(data).__name__}"
                )

            if data.seekable():
                data.seek(0)

            upload_kwargs = {
                "filename": data.filename,
                "caption": data.caption,
                "nbid": self._page.root.id,
                "pid": self._page.id,
                "change_description": "File uploaded via API",
            }

            if client_ip is not None:
                upload_kwargs["client_ip"] = client_ip

            entry_tree = self._user.api_post(
                "entries/add_attachment",
                data._backing,  # pyright: ignore[reportPrivateUsage, reportArgumentType]
                **upload_kwargs,
            )

            eid = extract_etree(entry_tree, {"entry": {"eid": str}})["eid"]
            entry = cls(eid, data.caption, self._user)
            entry._filename = data.filename or None  # pyright: ignore[reportPrivateUsage]
            entry._mime_type = data.mime_type or None  # pyright: ignore[reportPrivateUsage]

        else:
            if not isinstance(data, str):
                raise TypeError(
                    f"{cls.__name__} requires str data, got {type(data).__name__}"
                )
            entry_tree = self._user.api_post(
                "entries/add_entry",
                {"entry_data": data},
                part_type=cls._part_type,  # pyright: ignore[reportPrivateUsage]
                pid=self._page.id,
                nbid=self._page.root.id,
            )

            eid = extract_etree(entry_tree, {"entry": {"eid": str}})["eid"]
            entry = cls(eid, data, self._user)

        self._entries.append(entry)
        return entry
