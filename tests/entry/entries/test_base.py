"""Unit tests for Entry base class."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from labapi.entry.entries.attachment import AttachmentEntry
from labapi.entry.entries.base import Entry
from labapi.entry.entries.text import HeaderEntry, PlainTextEntry, TextEntry
from labapi.entry.entries.unknown import UnimplementedEntry, UnknownEntry
from labapi.entry.entries.widget import WidgetEntry
from labapi.user import User


class TestEntryUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_entry_id(self):
        """Test Entry stores and exposes its ID."""
        entry = TextEntry("eid_test", "<p>Content</p>", Mock(spec=User))
        assert entry.id == "eid_test"

    def test_direct_constructor_defaults_metadata_to_none(self):
        """Test existing three-argument constructors leave metadata unset."""
        entry = TextEntry("eid_test", "<p>Content</p>", Mock(spec=User))

        assert entry.created_at is None
        assert entry.updated_at is None
        assert entry.version is None

    def test_entry_content_type(self):
        """Test Entry exposes the correct content_type for its class."""
        assert TextEntry("e", "", Mock(spec=User)).content_type == "text entry"
        assert HeaderEntry("e", "", Mock(spec=User)).content_type == "heading"
        assert (
            PlainTextEntry("e", "", Mock(spec=User)).content_type == "plain text entry"
        )
        assert AttachmentEntry("e", "", Mock(spec=User)).content_type == "Attachment"
        assert (
            UnknownEntry(
                "e", "", Mock(spec=User), part_type="future entry"
            ).content_type
            == "future entry"
        )

    def test_unknown_entry_is_not_registered_for_literal_part_type(self):
        """Test UnknownEntry avoids reserving a plausible upstream part-type value."""
        assert Entry.is_registered("unknown entry") is False

    def test_unimplemented_entry_is_not_registered_for_literal_part_type(self):
        """Test UnimplementedEntry avoids reserving a plausible upstream part-type value."""
        assert Entry.is_registered("unimplemented entry") is False

    @pytest.mark.parametrize(
        ("part_type", "expected_class"),
        [
            ("text entry", TextEntry),
            ("plain text entry", PlainTextEntry),
            ("heading", HeaderEntry),
            ("Attachment", AttachmentEntry),
            ("sketch entry", UnimplementedEntry),
            ("equation entry", UnimplementedEntry),
            ("reference entry", UnimplementedEntry),
            ("assignment entry", UnimplementedEntry),
        ],
    )
    def test_current_entry_types_are_registered(
        self, part_type: str, expected_class: type
    ):
        """Test the current registration set."""
        assert Entry.is_registered(part_type) is True
        assert Entry.class_of(part_type) is expected_class

    def test_widget_entry_is_registered_for_backwards_compat(self):
        """Test widget entries stay registered to WidgetEntry for compatibility."""
        assert Entry.class_of("widget entry") is WidgetEntry


class TestEntryIntegration:
    """Integration tests with real objects and mocked API."""

    @pytest.mark.parametrize(
        ("part_type", "expected_class"),
        [
            ("text entry", TextEntry),
            ("plain text entry", PlainTextEntry),
            ("heading", HeaderEntry),
            ("Attachment", AttachmentEntry),
            ("sketch entry", UnimplementedEntry),
            ("equation entry", UnimplementedEntry),
            ("reference entry", UnimplementedEntry),
            ("assignment entry", UnimplementedEntry),
        ],
    )
    def test_entry_from_part_type_resolves_correctly(
        self, part_type: str, expected_class: type, user: User
    ):
        """Test registered part types resolve to their expected classes."""
        entry = Entry.from_part_type(part_type, "eid_123", "data", user)

        assert isinstance(entry, expected_class)
        assert entry.content_type == part_type

        # Attachment content is an object that triggers a download;
        # others are just strings.
        if not isinstance(entry, AttachmentEntry):
            assert entry.content == "data"

    def test_entry_from_part_type_widget_entry_returns_widget_entry(self, user: User):
        """Test widget entries resolve to the backward-compatible WidgetEntry class."""
        entry = Entry.from_part_type("widget entry", "eid_123", "data", user)

        assert type(entry) is WidgetEntry
        assert entry.content_type == "widget entry"
        assert entry.content == "data"

    def test_entry_from_part_type_unknown_returns_unknown_entry(self, user: User):
        """Test Entry.from_part_type falls back to UnknownEntry for unknown part types."""
        entry = Entry.from_part_type("unknown_type", "eid_999", "Data", user)

        assert isinstance(entry, UnknownEntry)
        assert entry.content_type == "unknown_type"
        assert entry.content == "Data"
