"""Unit tests for text-based entry classes."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from labapi.entry.entries.text import HeaderEntry, PlainTextEntry, TextEntry
from labapi.user import User


class TestTextEntryUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_text_entry_content_type(self):
        """Test TextEntry.content_type returns 'text entry'."""
        mock_user = Mock(spec=User)
        entry = TextEntry("eid_text", "<p>Content</p>", mock_user)

        assert entry.content_type == "text entry"

    def test_text_entry_content_getter(self):
        """Test TextEntry.content getter returns the entry data."""
        mock_user = Mock(spec=User)
        entry = TextEntry("eid_text", "<p>Test content</p>", mock_user)

        assert entry.content == "<p>Test content</p>"

    def test_header_entry_content_type(self):
        """Test HeaderEntry.content_type returns 'heading'."""
        mock_user = Mock(spec=User)
        entry = HeaderEntry("eid_header", "<h1>Header</h1>", mock_user)

        assert entry.content_type == "heading"

    def test_header_entry_content_getter(self):
        """Test HeaderEntry.content getter returns the entry data."""
        mock_user = Mock(spec=User)
        entry = HeaderEntry("eid_header", "<h1>My Header</h1>", mock_user)

        assert entry.content == "<h1>My Header</h1>"

    def test_plain_text_entry_content_type(self):
        """Test PlainTextEntry.content_type returns 'plain text entry'."""
        mock_user = Mock(spec=User)
        entry = PlainTextEntry("eid_plain", "Plain text", mock_user)

        assert entry.content_type == "plain text entry"

    def test_plain_text_entry_content_getter(self):
        """Test PlainTextEntry.content getter returns the entry data."""
        mock_user = Mock(spec=User)
        entry = PlainTextEntry("eid_plain", "This is plain text", mock_user)

        assert entry.content == "This is plain text"

    def test_content_setter_rejects_none(self):
        """Test that setting content to None raises TypeError."""
        mock_user = Mock(spec=User)
        entry = TextEntry("eid_text", "original", mock_user)

        with pytest.raises(TypeError, match="content must be a str, got NoneType"):
            entry.content = None  # type: ignore[assignment]  # intentional bad type

        mock_user.api_post.assert_not_called()
        assert entry.content == "original"

    def test_content_setter_rejects_non_str(self):
        """Test that setting content to a non-str raises TypeError."""
        mock_user = Mock(spec=User)
        entry = PlainTextEntry("eid_plain", "original", mock_user)

        with pytest.raises(TypeError, match="content must be a str, got int"):
            entry.content = 42  # type: ignore[assignment]  # intentional bad type

        mock_user.api_post.assert_not_called()
        assert entry.content == "original"


class TestTextEntryIntegration:
    """Integration tests with real objects and mocked API."""

    def test_text_entry_content_setter(self, client, user: User):
        """Test TextEntry.content setter updates via API."""
        entry = TextEntry("eid_text", "<p>Old content</p>", user)

        # Mock API response
        client.api_response = client.xml(
            "entry",
            client.xml("success", True),
        )

        # Update content
        entry.content = "<p>New content</p>"

        # Verify API call was made with correct parameters
        api_call = client.pop_api_call()
        assert api_call[0] == "entries/update_entry"
        assert api_call[1]["entry_data"] == "<p>New content</p>"
        assert api_call[1]["eid"] == "eid_text"

        # Verify content was updated locally
        assert entry.content == "<p>New content</p>"

    def test_header_entry_content_setter(self, client, user: User):
        """Test HeaderEntry.content setter updates via API."""
        entry = HeaderEntry("eid_header", "<h1>Old Header</h1>", user)

        client.api_response = client.xml(
            "entry",
            client.xml("success", True),
        )

        entry.content = "<h1>New Header</h1>"

        api_call = client.pop_api_call()
        assert api_call[0] == "entries/update_entry"
        assert api_call[1]["entry_data"] == "<h1>New Header</h1>"
        assert entry.content == "<h1>New Header</h1>"

    def test_plain_text_entry_content_setter(self, client, user: User):
        """Test PlainTextEntry.content setter updates via API."""
        entry = PlainTextEntry("eid_plain", "Old text", user)

        client.api_response = client.xml(
            "entry",
            client.xml("success", True),
        )

        entry.content = "New text"

        api_call = client.pop_api_call()
        assert api_call[0] == "entries/update_entry"
        assert api_call[1]["entry_data"] == "New text"
        assert entry.content == "New text"
