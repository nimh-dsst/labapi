"""Unit tests for Entries collection class."""

from __future__ import annotations

from io import BytesIO
from typing import Any, cast
from unittest.mock import Mock

import pytest

from labapi.entry.attachment import Attachment
from labapi.entry.collection import Entries
from labapi.entry.entries import (
    AttachmentEntry,
    HeaderEntry,
    PlainTextEntry,
    TextEntry,
    UnimplementedEntry,
    UnknownEntry,
    WidgetEntry,
)
from labapi.user import User


class TestEntriesUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_entries_len(self):
        """Test Entries.__len__ returns correct number of entries."""
        mock_user = Mock(spec=User)
        mock_page = Mock()

        entry1 = TextEntry("eid_1", "<p>Entry 1</p>", mock_user)
        entry2 = HeaderEntry("eid_2", "<h1>Header</h1>", mock_user)
        entry3 = PlainTextEntry("eid_3", "Plain text", mock_user)

        entries = Entries([entry1, entry2, entry3], mock_user, mock_page)

        assert len(entries) == 3

    def test_entries_getitem_by_index(self):
        """Test Entries.__getitem__ with integer index."""
        mock_user = Mock(spec=User)
        mock_page = Mock()

        entry1 = TextEntry("eid_1", "<p>Entry 1</p>", mock_user)
        entry2 = HeaderEntry("eid_2", "<h1>Header</h1>", mock_user)

        entries = Entries([entry1, entry2], mock_user, mock_page)

        assert entries[0] is entry1
        assert entries[1] is entry2
        assert entries[0].id == "eid_1"
        assert entries[1].id == "eid_2"

    def test_entries_getitem_by_slice(self):
        """Test Entries.__getitem__ with slice returns list snapshot."""
        mock_user = Mock(spec=User)
        mock_page = Mock()

        entry1 = TextEntry("eid_1", "<p>Entry 1</p>", mock_user)
        entry2 = HeaderEntry("eid_2", "<h1>Header</h1>", mock_user)
        entry3 = PlainTextEntry("eid_3", "Plain text", mock_user)

        entries = Entries([entry1, entry2, entry3], mock_user, mock_page)

        sliced = entries[0:2]
        assert isinstance(sliced, list)
        assert len(sliced) == 2
        assert sliced[0].id == "eid_1"
        assert sliced[1].id == "eid_2"

    def test_entries_getitem_by_id(self):
        """Test Entries.__getitem__ with string entry id."""
        mock_user = Mock(spec=User)
        mock_page = Mock()

        entry1 = TextEntry("eid_1", "<p>Entry 1</p>", mock_user)
        entry2 = HeaderEntry("eid_2", "<h1>Header</h1>", mock_user)
        entries = Entries([entry1, entry2], mock_user, mock_page)

        assert entries["eid_1"] is entry1
        assert entries["eid_2"] is entry2

        with pytest.raises(KeyError, match="Entry with id 'missing' not found"):
            _ = entries["missing"]

    def test_entries_iter(self):
        """Test Entries.__iter__ returns iterator over entries."""
        mock_user = Mock(spec=User)
        mock_page = Mock()

        entry1 = TextEntry("eid_1", "<p>Entry 1</p>", mock_user)
        entry2 = HeaderEntry("eid_2", "<h1>Header</h1>", mock_user)
        entry3 = PlainTextEntry("eid_3", "Plain text", mock_user)

        entries = Entries([entry1, entry2, entry3], mock_user, mock_page)

        entry_ids = [entry.id for entry in entries]
        assert entry_ids == ["eid_1", "eid_2", "eid_3"]

    def test_entries_create_attachment_requires_attachment_data(self):
        """Test attachment entry creation rejects non-attachment payloads."""
        mock_user = Mock(spec=User)
        mock_page = Mock()
        mock_page.id = "test_page_id"
        mock_page.root = Mock()
        mock_page.root.id = "test_notebook_id"
        entries = Entries([], mock_user, mock_page)

        with pytest.raises(TypeError, match="AttachmentEntry requires Attachment"):
            entries.create(AttachmentEntry, "not an attachment")

        mock_user.api_post.assert_not_called()

    def test_entries_create_text_requires_str_data(self):
        """Test text entry creation rejects non-string payloads."""
        mock_user = Mock(spec=User)
        mock_page = Mock()
        mock_page.id = "test_page_id"
        mock_page.root = Mock()
        mock_page.root.id = "test_notebook_id"
        entries = Entries([], mock_user, mock_page)

        attachment = Attachment(
            backing=BytesIO(b"File content"),
            mime_type="text/plain",
            filename="test.txt",
            caption="Test file",
        )

        with pytest.raises(TypeError, match="TextEntry requires str data"):
            entries.create(TextEntry, cast(Any, attachment))

        mock_user.api_post.assert_not_called()

    @pytest.mark.parametrize("cls", [UnknownEntry, UnimplementedEntry, WidgetEntry])
    def test_entries_create_rejects_unsupported_wrappers(self, cls: type[Any]):
        """Test unsupported fallback entry wrappers are rejected before API calls."""
        mock_user = Mock(spec=User)
        mock_page = Mock()
        mock_page.id = "test_page_id"
        mock_page.root = Mock()
        mock_page.root.id = "test_notebook_id"
        entries = Entries([], mock_user, mock_page)

        with pytest.raises(TypeError, match=f"{cls.__name__} cannot be created"):
            entries.create(cast(Any, cls), "payload")

        mock_user.api_post.assert_not_called()

    def test_entries_iter_snapshot_stable_after_mutation(self):
        """Entries iteration should remain stable after later mutations."""
        mock_user = Mock(spec=User)
        mock_page = Mock()

        entry1 = TextEntry("eid_1", "<p>Entry 1</p>", mock_user)
        entry2 = HeaderEntry("eid_2", "<h1>Header</h1>", mock_user)
        entry3 = PlainTextEntry("eid_3", "Plain text", mock_user)

        entries = Entries([entry1, entry2], mock_user, mock_page)
        iterator = iter(entries)

        assert next(iterator).id == "eid_1"

        entries._entries.append(entry3)  # pyright: ignore[reportPrivateUsage]
        assert next(iterator).id == "eid_2"
        with pytest.raises(StopIteration):
            next(iterator)

    def test_entries_reversed_snapshot_stable_after_mutation(self):
        """Reverse iteration should remain stable after later mutations."""
        mock_user = Mock(spec=User)
        mock_page = Mock()

        entry1 = TextEntry("eid_1", "<p>Entry 1</p>", mock_user)
        entry2 = HeaderEntry("eid_2", "<h1>Header</h1>", mock_user)
        entry3 = PlainTextEntry("eid_3", "Plain text", mock_user)

        entries = Entries([entry1, entry2], mock_user, mock_page)
        iterator = reversed(entries)

        assert next(iterator).id == "eid_2"

        entries._entries.append(entry3)  # pyright: ignore[reportPrivateUsage]
        assert next(iterator).id == "eid_1"
        with pytest.raises(StopIteration):
            next(iterator)

    def test_create_json_entry_raises_partial_error_on_text_failure(self):
        """Test create_json_entry raises PartialEntryCreateError if text entry fails."""
        from lxml.etree import fromstring

        from labapi.exceptions import PartialEntryCreateError

        mock_user = Mock(spec=User)
        mock_page = Mock()
        mock_page.id = "pid"
        mock_page.root.id = "nbid"

        def mock_api_post(method, *_args, **_kwargs):
            if method == "entries/add_attachment":
                return fromstring(
                    b"<response><entry><eid>att-1</eid></entry></response>"
                )
            if method == "entries/add_entry":
                raise RuntimeError("API failure")
            raise AssertionError(f"Unexpected API call: {method}")

        mock_user.api_post.side_effect = mock_api_post

        entries = Entries([], mock_user, mock_page)

        with pytest.raises(PartialEntryCreateError) as exc_info:
            entries.create_json_entry({"data": "val"}, filename="data.json")

        assert "Failed to create companion text entry" in str(exc_info.value)
        assert exc_info.value.partial_entry.id == "att-1"
        assert exc_info.value.partial_entry in entries


class TestEntriesIntegration:
    """Integration tests with real objects and mocked API."""

    @pytest.fixture
    def mock_page(self, user: User):
        """Create a mock NotebookPage for testing."""
        page = Mock()
        page.id = "test_page_id"
        page.root = Mock()
        page.root.id = "test_notebook_id"
        page._user = user
        return page

    @pytest.mark.parametrize(
        ("cls", "data"),
        [
            (TextEntry, "<p>New content</p>"),
            (HeaderEntry, "<h1>Title</h1>"),
            (PlainTextEntry, "Plain text content"),
        ],
    )
    def test_entries_create_text_types(self, client, user: User, mock_page, cls, data):
        """Test Entries.create dispatches correctly for all text entry types."""
        entries = Entries([], user, mock_page)

        client.api_response = client.entries_response(client.entry_xml("new_eid"))

        entry = entries.create(cls, data)

        assert isinstance(entry, cls)
        assert entry.id == "new_eid"
        assert len(entries) == 1
        assert entries[0] is entry

        api_call = client.pop_api_call()
        assert api_call[0] == "entries/add_entry"
        assert api_call[1]["entry_data"] == data
        assert api_call[1]["pid"] == "test_page_id"
        assert api_call[1]["nbid"] == "test_notebook_id"

    def test_entries_create_attachment(self, client, user: User, mock_page):
        """Test Entries.create with attachment type."""
        entries = Entries([], user, mock_page)

        client.api_response = client.entries_response(
            client.entry_xml("new_attachment_eid")
        )

        # Create attachment
        backing = BytesIO(b"File content")
        attachment = Attachment(
            backing=backing,
            mime_type="text/plain",
            filename="test.txt",
            caption="Test file",
        )

        entry = entries.create(AttachmentEntry, attachment)

        assert isinstance(entry, AttachmentEntry)
        assert entry.id == "new_attachment_eid"
        assert entry.caption == "Test file"
        assert len(entries) == 1

        # Verify API call
        api_call = client.pop_api_call()
        assert api_call[0] == "entries/add_attachment"
        assert api_call[1]["filename"] == "test.txt"
        assert api_call[1]["caption"] == "Test file"
        assert api_call[1]["pid"] == "test_page_id"
        assert api_call[1]["nbid"] == "test_notebook_id"
        assert "client_ip" not in api_call[1]

    def test_entries_create_attachment_with_client_ip(
        self, client, user: User, mock_page
    ):
        """Test Entries.create passes through client_ip for attachment uploads."""
        entries = Entries([], user, mock_page)

        client.api_response = client.entries_response(
            client.entry_xml("new_attachment_eid")
        )

        attachment = Attachment(
            backing=BytesIO(b"File content"),
            mime_type="text/plain",
            filename="test.txt",
            caption="Test file",
        )

        entries.create(AttachmentEntry, attachment, client_ip="203.0.113.7")

        api_call = client.pop_api_call()
        assert api_call[0] == "entries/add_attachment"
        assert api_call[1]["client_ip"] == "203.0.113.7"

    def test_entries_create_attachment_rewinds_seekable_stream(
        self, client, user: User, mock_page
    ):
        """Test Entries.create rewinds seekable attachments before upload."""
        entries = Entries([], user, mock_page)

        client.api_response = client.entries_response(
            client.entry_xml("rewound_attachment_eid")
        )

        backing = BytesIO(b"File content")
        attachment = Attachment(
            backing=backing,
            mime_type="text/plain",
            filename="test.txt",
            caption="Test file",
        )
        attachment.read(4)

        entries.create(AttachmentEntry, attachment)

        assert backing.tell() == 0
        _ = client.pop_api_call()

    def test_entries_create_json_entry(self, client, user: User, mock_page):
        """Test Entries.create_json_entry creates both attachment and text entry."""
        entries = Entries([], user, mock_page)

        # Mock API responses (first for attachment, then for text)
        client.api_response = client.entries_response(
            client.entry_xml("json_attachment_eid")
        )
        client.api_response = client.entries_response(client.entry_xml("json_text_eid"))

        # Create JSON entry
        data = {"key": "value", "number": 42}
        file_entry, text_entry = entries.create_json_entry(data)

        # Verify both entries were created
        assert isinstance(file_entry, AttachmentEntry)
        assert isinstance(text_entry, TextEntry)
        assert file_entry.id == "json_attachment_eid"
        assert text_entry.id == "json_text_eid"

        # Verify both entries were added to collection
        assert len(entries) == 2
        assert entries[0] is file_entry
        assert entries[1] is text_entry

        # Verify text entry contains reference to attachment
        assert "uploaded_data_" in text_entry.content
        assert ".json" in text_entry.content
        assert file_entry.id in text_entry.content
        client.clear_api_calls()

    def test_entries_create_json_entry_custom_filename_and_caption(
        self, client, user: User, mock_page
    ):
        """Test Entries.create_json_entry accepts stable filename and caption overrides."""
        entries = Entries([], user, mock_page)

        client.api_response = client.entries_response(
            client.entry_xml("json_attachment_eid")
        )
        client.api_response = client.entries_response(client.entry_xml("json_text_eid"))

        file_entry, text_entry = entries.create_json_entry(
            {"key": "value"},
            filename="metrics.json",
            caption="Metrics Snapshot",
        )

        assert file_entry.caption == "Metrics Snapshot"
        assert text_entry.content.startswith(
            "\n<p>Reference Attachment: Metrics Snapshot</p>"
        )
        assert "json_attachment_eid" in text_entry.content

        attachment_call = client.pop_api_call()
        assert attachment_call[0] == "entries/add_attachment"
        assert attachment_call[1]["filename"] == "metrics.json"
        assert attachment_call[1]["caption"] == "Metrics Snapshot"

        text_call = client.pop_api_call()
        assert text_call[0] == "entries/add_entry"
        assert "Metrics Snapshot" in text_call[1]["entry_data"]

    def test_entries_create_json_entry_escapes_html_in_preview(
        self, client, user: User, mock_page
    ):
        """Test JSON preview HTML escapes caption and JSON payload values."""
        entries = Entries([], user, mock_page)

        client.api_response = client.entries_response(
            client.entry_xml("json_attachment_eid")
        )
        client.api_response = client.entries_response(client.entry_xml("json_text_eid"))

        caption = '<script>alert("x")</script> & metrics'
        data = {
            "headline": "<b>danger</b>",
            "closing": "</pre>",
        }

        file_entry, text_entry = entries.create_json_entry(
            data,
            filename="metrics.json",
            caption=caption,
        )

        assert file_entry.caption == caption
        assert (
            "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; metrics"
            in text_entry.content
        )
        assert "&lt;b&gt;danger&lt;/b&gt;" in text_entry.content
        assert "&lt;/pre&gt;" in text_entry.content
        assert text_entry.content.count("</pre>") == 1

        attachment_call = client.pop_api_call()
        assert attachment_call[0] == "entries/add_attachment"
        assert attachment_call[1]["caption"] == caption

        text_call = client.pop_api_call()
        assert text_call[0] == "entries/add_entry"
        assert "<script>alert(" not in text_call[1]["entry_data"]
        assert (
            "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; metrics"
            in text_call[1]["entry_data"]
        )
