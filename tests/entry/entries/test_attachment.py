"""Unit tests for AttachmentEntry class."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import Mock

from labapi.client import StreamingResponse
from labapi.entry.attachment import Attachment
from labapi.entry.entries.attachment import AttachmentEntry
from labapi.user import User


class TestAttachmentEntryUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_attachment_entry_content_type(self):
        """Test AttachmentEntry.content_type returns 'Attachment'."""
        mock_user = Mock(spec=User)
        entry = AttachmentEntry("eid_att", "Test caption", mock_user)

        assert entry.content_type == "Attachment"

    def test_attachment_entry_caption(self):
        """Test AttachmentEntry.caption property returns the caption."""
        mock_user = Mock(spec=User)
        entry = AttachmentEntry("eid_att", "My attachment caption", mock_user)

        assert entry.caption == "My attachment caption"


class TestAttachmentEntryIntegration:
    """Integration tests with real objects and mocked API."""

    def test_attachment_entry_get_attachment(self, client, user: User):
        """Test AttachmentEntry.get_attachment fetches and caches attachment."""
        entry = AttachmentEntry("eid_att", "Test file", user)

        # Mock the stream_api_get method
        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Disposition": 'attachment; filename="test.txt"',
        }

        mock_response.iter_content.return_value = [b"Test ", b"file ", b"content"]
        client.stream_api_get = Mock(return_value=StreamingResponse(mock_response))

        # Get attachment
        attachment = entry.get_attachment(use_tempfile=False)

        # Verify attachment properties
        assert isinstance(attachment, Attachment)
        assert attachment.filename == "test.txt"
        assert attachment.mime_type == "text/plain"
        assert attachment.caption == "Test file"

        # Verify content
        assert attachment.read() == b"Test file content"

        # Verify API was called correctly
        client.stream_api_get.assert_called_once_with(
            "entries/entry_attachment", uid=user.id, eid="eid_att"
        )

    def test_attachment_entry_content_getter(self, client, user: User):
        """Test AttachmentEntry.content getter returns attachment."""
        entry = AttachmentEntry("eid_att", "Caption", user)

        # Mock stream_api_get
        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="document.pdf"',
        }

        mock_response.iter_content.return_value = [b"PDF content"]
        client.stream_api_get = Mock(return_value=StreamingResponse(mock_response))

        # Access content property
        attachment = entry.content

        assert isinstance(attachment, Attachment)
        assert attachment.filename == "document.pdf"
        assert attachment.mime_type == "application/pdf"

    def test_attachment_entry_content_setter(self, client, user: User):
        """Test AttachmentEntry.content setter uploads attachment."""
        entry = AttachmentEntry("eid_att", "Old caption", user)

        # Create a new attachment to upload
        backing = BytesIO(b"New file content")
        new_attachment = Attachment(
            backing=backing,
            mime_type="text/plain",
            filename="new_file.txt",
            caption="New caption",
        )

        # Mock API response
        client.api_response = client.xml(
            "entry",
            client.xml("success", True),
        )

        # Update content
        entry.content = new_attachment

        # Verify API call
        api_call = client.pop_api_call()
        assert api_call[0] == "entries/update_attachment"
        assert api_call[1]["filename"] == "new_file.txt"
        assert api_call[1]["caption"] == "New caption"
        assert api_call[1]["eid"] == "eid_att"

    def test_attachment_entry_content_setter_rewinds_seekable_stream(
        self, client, user: User
    ):
        """Test AttachmentEntry.content rewinds seekable uploads before API calls."""
        entry = AttachmentEntry("eid_att", "Old caption", user)

        backing = BytesIO(b"New file content")
        new_attachment = Attachment(
            backing=backing,
            mime_type="text/plain",
            filename="new_file.txt",
            caption="New caption",
        )
        new_attachment.read(4)

        client.api_response = client.xml(
            "entry",
            client.xml("success", True),
        )

        entry.content = new_attachment

        assert backing.tell() == 0
        _ = client.pop_api_call()

    def test_attachment_entry_get_attachment_caching(self, client, user: User):
        """Test AttachmentEntry.get_attachment reuses download cache without sharing handles."""
        entry = AttachmentEntry("eid_att", "Caption", user)

        # Mock stream_api_get
        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "text/plain",
            "Content-Disposition": 'attachment; filename="test.txt"',
        }

        mock_response.iter_content.return_value = [b"Content"]
        client.stream_api_get = Mock(return_value=StreamingResponse(mock_response))

        # First call
        attachment1 = entry.get_attachment()
        assert client.stream_api_get.call_count == 1

        # Second call should use cached data
        attachment2 = entry.get_attachment()
        assert client.stream_api_get.call_count == 1  # Not called again

        assert attachment1 is not attachment2

        attachment1.read(1)
        assert attachment2.read() == b"Content"

        attachment1.close()
        attachment3 = entry.get_attachment()
        assert client.stream_api_get.call_count == 1
        assert attachment3.read() == b"Content"

    def test_get_attachment_tempfile_copies_in_chunks(self, client, user: User):
        """get_attachment(use_tempfile=True) must not read the full payload at once.

        Regression for #215: the old code called self._filedata.read() with no
        size, materializing the entire cached payload as one bytes object.
        """
        entry = AttachmentEntry("eid_att", "Caption", user)

        mock_response = Mock()
        mock_response.headers = {
            "Content-Type": "text/plain",
            "Content-Disposition": 'attachment; filename="test.txt"',
        }
        mock_response.iter_content.return_value = [b"Chunked content"]
        client.stream_api_get = Mock(return_value=StreamingResponse(mock_response))

        attachment = entry.get_attachment(use_tempfile=True)
        assert attachment.read() == b"Chunked content"
        attachment.close()
