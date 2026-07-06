"""Attachment Entry Module."""

from __future__ import annotations

from email.message import Message
from io import BytesIO
from tempfile import TemporaryFile
from typing import IO, TYPE_CHECKING

from typing_extensions import override

from labapi.entry.attachment import Attachment
from labapi.exceptions import ApiError

from .base import Entry

if TYPE_CHECKING:
    from labapi.user import User


def _make_backing_io(use_tempfile: bool) -> IO[bytes]:
    return TemporaryFile() if use_tempfile else BytesIO()


class AttachmentEntry(Entry[Attachment], part_type="Attachment"):
    """Represents an attachment entry on a LabArchives page.

    This class handles the retrieval and updating of file attachments,
    providing access to the attachment's content, filename, and caption.
    """

    def __init__(self, eid: str, caption: str, user: User):
        """Initialize an attachment entry.

        :param eid: The unique ID of the entry.
        :param caption: The caption associated with the attachment.
        :param user: The authenticated user.
        """
        super().__init__(eid, caption, user)
        self._filedata: Attachment | None = None
        self._filename: str | None = None
        self._mime_type: str | None = None

    def _ensure_attachment(self, use_tempfile: bool) -> None:
        if self._filedata is None or self._filedata.closed:
            output = _make_backing_io(use_tempfile)

            with self._user.client.stream_api_get(
                "entries/entry_attachment", uid=self._user.id, eid=self.id
            ) as attachment_stream:
                for chunk in attachment_stream:
                    output.write(chunk)

            headers = attachment_stream.headers

            msg = Message()
            msg["Content-Type"] = (
                headers.get("Content-Type") or "application/octet-stream"
            )
            msg["Content-Disposition"] = headers.get("Content-Disposition")
            filename = msg.get_filename()
            mime_type = msg.get_content_type()

            if filename is None:
                raise ApiError("Could not determine filename from API response headers")

            self._filedata = Attachment(output, mime_type, filename, self._data)

    def get_attachment(self, use_tempfile: bool = False) -> Attachment:
        """Return the attachment payload as an independent stream copy.

        The attachment data is fetched from the LabArchives API on first call
        and cached.

        :param use_tempfile: If True, the attachment data will be stored in a
                             temporary file; otherwise, in an in-memory BytesIO object.
                             Defaults to False.
        :returns: An :class:`~labapi.entry.attachment.Attachment` object containing the file data and metadata.
        """
        self._ensure_attachment(use_tempfile)

        assert self._filedata is not None
        output = _make_backing_io(use_tempfile)

        # Return an independent copy so each caller gets isolated read/seek/close state
        # while still sharing a single downloaded backing attachment in the cache.
        self._filedata.seek(0)
        output.write(self._filedata.read())
        output.seek(0)

        return Attachment(
            output,
            self._filedata.mime_type,
            self._filedata.filename,
            self._filedata.caption,
        )

    @property
    @override
    def content(self) -> Attachment:
        """Return the attachment content.

        This property retrieves the attachment data, caching it for subsequent access.

        :returns: The attachment object.
        """
        return self.get_attachment()

    @content.setter
    @override
    def content(self, value: Attachment):
        """Set the attachment content.

        This operation updates the attachment in LabArchives via an API call
        and invalidates any previously cached attachment data.

        :param value: The new attachment object to upload.
        """
        # NOTE: this implicitly invalidates all previous Attachments
        # NOTE: if every time content is called we give a new copy anyways that's fine
        #       (see get_attachment())
        if value._backing.seekable():  # pyright: ignore[reportPrivateUsage]
            value._backing.seek(0)  # pyright: ignore[reportPrivateUsage]

        self._user.api_post(
            "entries/update_attachment",
            value._backing,  # pyright: ignore[reportPrivateUsage, reportArgumentType]
            filename=value.filename,
            caption=value.caption,
            eid=self.id,
            change_description="File updated via API",
        )

        self._data = value.caption

        if self._filedata:
            self._filedata.close()
        self._filedata = None

    @property
    def caption(self) -> str:
        """Return the attachment caption.

        :returns: The caption string.
        """
        return self._data
