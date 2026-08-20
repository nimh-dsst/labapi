"""Unit tests for NotebookPage class."""

from __future__ import annotations

import warnings
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import Mock

import pytest

from labapi import Index, Notebook, NotebookPage
from labapi.entry import Attachment, AttachmentEntry, Entries, UnknownEntry, WidgetEntry
from labapi.user import User


class TestNotebookPageUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_page_properties(self):
        """Test NotebookPage basic properties."""
        mock_user = Mock(spec=User)
        mock_root = Mock(spec=Notebook)
        mock_parent = Mock(spec=Notebook)

        page = NotebookPage(
            tree_id="page-1",
            name="Test Page",
            parent=mock_parent,
            root=mock_root,
            user=mock_user,
        )

        assert page.id == "page-1"
        assert page.name == "Test Page"
        assert page.parent is mock_parent
        assert page.root is mock_root
        assert page.is_dir() is False

    def test_copy_to_copies_attachment_and_closes_attachment(self):
        """Test NotebookPage.copy_to uploads attachments and closes local handles."""
        source_page = Mock(spec=NotebookPage)
        source_page.name = "Source Page"
        source_page.id = "source-page-id"

        attachment = Attachment(
            BytesIO(b"attachment payload"),
            "application/octet-stream",
            "example.bin",
            "attachment caption",
        )

        attachment_entry = Mock()
        attachment_entry.id = "entry-attachment-1"
        attachment_entry.content_type = "Attachment"
        attachment_entry.content = attachment

        source_page.entries = [attachment_entry]

        new_page_entries = Mock()
        new_page = Mock(spec=NotebookPage)
        new_page.id = "new-page-id"
        new_page.entries = new_page_entries

        destination = Mock()
        destination.create.return_value = new_page

        NotebookPage.copy_to(source_page, destination)

        destination.create.assert_called_once()
        new_page_entries.create.assert_called_once_with(
            attachment_entry.__class__, attachment
        )
        assert attachment.closed is True

    def test_copy_to_warns_and_continues_when_attachment_copy_fails(self):
        """Test NotebookPage.copy_to warns and skips entries that fail to copy."""
        source_page = Mock(spec=NotebookPage)
        source_page.name = "Source Page"
        source_page.id = "source-page-id"

        attachment = Attachment(
            BytesIO(b"attachment payload"),
            "application/octet-stream",
            "example.bin",
            "attachment caption",
        )

        attachment_entry = Mock()
        attachment_entry.id = "entry-attachment-1"
        attachment_entry.content_type = "Attachment"
        attachment_entry.content = attachment
        source_page.entries = [attachment_entry]

        new_page_entries = Mock()
        new_page_entries.create.side_effect = RuntimeError("upload failed")

        new_page = Mock(spec=NotebookPage)
        new_page.id = "new-page-id"
        new_page.entries = new_page_entries

        destination = Mock()
        destination.create.return_value = new_page

        with pytest.warns(RuntimeWarning, match="This entry was skipped"):
            NotebookPage.copy_to(source_page, destination)

        new_page_entries.create.assert_called_once_with(
            attachment_entry.__class__, attachment
        )
        assert attachment.closed is True

    def test_copy_to_warns_and_continues_when_entry_create_raises(self):
        """Test NotebookPage.copy_to catches per-entry create failures and continues."""
        source_page = Mock(spec=NotebookPage)
        source_page.name = "Source Page"
        source_page.id = "source-page-id"

        failing_entry = Mock()
        failing_entry.id = "entry-text-1"
        failing_entry.content_type = "Text"
        failing_entry.content = "<p>bad</p>"

        succeeding_entry = Mock()
        succeeding_entry.id = "entry-text-2"
        succeeding_entry.content_type = "Text"
        succeeding_entry.content = "<p>ok</p>"
        source_page.entries = [failing_entry, succeeding_entry]

        new_page_entries = Mock()
        new_page_entries.create.side_effect = [ValueError("create failed"), None]

        new_page = Mock(spec=NotebookPage)
        new_page.id = "new-page-id"
        new_page.entries = new_page_entries

        destination = Mock()
        destination.create.return_value = new_page

        with pytest.warns(RuntimeWarning, match="This entry was skipped"):
            NotebookPage.copy_to(source_page, destination)

        assert new_page_entries.create.call_count == 2
        assert new_page_entries.create.call_args_list[0].args == (
            failing_entry.__class__,
            failing_entry.content,
        )
        assert new_page_entries.create.call_args_list[1].args == (
            succeeding_entry.__class__,
            succeeding_entry.content,
        )

    def test_copy_to_warns_and_continues_when_attachment_fetch_fails(self):
        """Test NotebookPage.copy_to warns and continues when reading attachment content fails."""
        source_page = Mock(spec=NotebookPage)
        source_page.name = "Source Page"
        source_page.id = "source-page-id"

        class FailingAttachmentEntry:
            id = "entry-attachment-1"
            content_type = "Attachment"

            @property
            def content(self):
                raise RuntimeError("download failed")

        failing_entry = FailingAttachmentEntry()

        succeeding_entry = Mock()
        succeeding_entry.id = "entry-text-2"
        succeeding_entry.content_type = "Text"
        succeeding_entry.content = "<p>ok</p>"
        source_page.entries = [failing_entry, succeeding_entry]

        new_page_entries = Mock()
        new_page = Mock(spec=NotebookPage)
        new_page.id = "new-page-id"
        new_page.entries = new_page_entries

        destination = Mock()
        destination.create.return_value = new_page

        with pytest.warns(RuntimeWarning, match="This entry was skipped"):
            NotebookPage.copy_to(source_page, destination)

        new_page_entries.create.assert_called_once_with(
            succeeding_entry.__class__, succeeding_entry.content
        )


class TestNotebookPageIntegration:
    """Integration tests with real objects and mocked API."""

    def test_page_from_tree(self, notebook_tree: Notebook):
        """Test NotebookPage identity and name from the tree fixture."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        assert page.id == "page-1"
        assert page.name == "Test Page 1"

    def test_page_entries_lazy_load(self, client, notebook_tree: Notebook):
        """Test NotebookPage.entries lazily loads from API."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        client.clear_api_calls()

        # Mock API response for entries
        client.api_response = client.entries_response(
            client.entry_xml(
                "entry_1",
                part_type="text entry",
                entry_data="<p>Test content</p>",
            ),
            client.entry_xml(
                "entry_2",
                part_type="heading",
                entry_data="<h1>Header</h1>",
            ),
            include_response=False,
        )

        entries = page.entries

        assert isinstance(entries, Entries)
        assert len(entries) == 2
        assert entries[0].created_at is None
        assert entries[0].updated_at is None
        assert entries[0].version is None

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/get_entries_for_page"
        assert api_call[1]["page_tree_id"] == "page-1"
        assert api_call[1]["nbid"] == notebook_tree.id
        assert api_call[1]["entry_data"] is True
        client.clear_api_calls()

    def test_page_entries_extract_optional_metadata(
        self, client, notebook_tree: Notebook
    ):
        """Test page entries preserve API timestamps and versions."""
        page = notebook_tree[Index.Id : "page-1"].as_page()
        client.clear_api_calls()
        client.api_response = client.entries_response(
            client.xml(
                "entry",
                client.xml("eid", "entry_1"),
                client.xml("part-type", "text entry"),
                client.xml("created-at", "2026-07-29T22:12:57Z"),
                client.xml("updated-at", "2026-07-30T01:02:03Z"),
                client.xml("version", "1"),
                client.xml("entry-data", "<p>Test content</p>"),
            ),
            include_response=False,
        )

        entry = page.entries[0]

        assert entry.created_at == datetime(
            2026, 7, 29, 22, 12, 57, tzinfo=timezone.utc
        )
        assert entry.updated_at == datetime(2026, 7, 30, 1, 2, 3, tzinfo=timezone.utc)
        assert entry.version == 1
        client.clear_api_calls()

    def test_page_entries_caching(self, client, notebook_tree: Notebook):
        """Test NotebookPage.entries caches the result."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        client.clear_api_calls()

        client.api_response = client.entries_response(
            client.entry_xml(
                "entry_1",
                part_type="text entry",
                entry_data="<p>Content</p>",
            ),
            include_response=False,
        )

        entries1 = page.entries
        _ = client.pop_api_call()  # consume the load call

        entries2 = page.entries

        assert entries1 is entries2
        client.clear_api_calls()

    def test_page_entries_wrap_sketch_entry_as_unimplemented(
        self, client, notebook_tree: Notebook
    ):
        """Test NotebookPage.entries currently wraps sketch entries as unimplemented."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        client.clear_api_calls()

        client.api_response = client.entries_response(
            client.entry_xml(
                "entry_unknown_known",
                part_type="sketch entry",
                entry_data="sketch payload",
            ),
            include_response=False,
        )

        from labapi.entry import UnimplementedEntry

        with pytest.warns(UserWarning, match="Wrapping as UnimplementedEntry"):
            entries = page.entries

        assert len(entries) == 1
        assert isinstance(entries[0], UnimplementedEntry)
        assert entries[0].content_type == "sketch entry"
        assert entries[0].content == "sketch payload"
        _ = client.pop_api_call()
        client.clear_api_calls()

    def test_page_entries_wrap_unknown_type(self, client, notebook_tree: Notebook):
        """Test NotebookPage.entries preserves truly unknown entries."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        client.clear_api_calls()

        client.api_response = client.entries_response(
            client.entry_xml(
                "entry_unknown_new",
                part_type="future entry",
                entry_data="future payload",
            ),
            include_response=False,
        )

        with pytest.warns(RuntimeWarning, match="Wrapping as UnknownEntry"):
            entries = page.entries

        assert len(entries) == 1
        assert isinstance(entries[0], UnknownEntry)
        assert entries[0].content_type == "future entry"
        assert entries[0].content == "future payload"
        _ = client.pop_api_call()
        client.clear_api_calls()

    def test_page_entries_wrap_unknown_type_without_optional_fields(
        self, client, notebook_tree: Notebook
    ):
        """Test page loading preserves unknown entries without optional fields."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        client.clear_api_calls()
        client.api_response = client.entries_response(
            client.xml(
                "entry",
                client.xml("eid", "entry_unknown_new"),
                client.xml("part-type", "future entry"),
            ),
            include_response=False,
        )

        with pytest.warns(RuntimeWarning, match="Wrapping as UnknownEntry"):
            entries = page.entries

        assert len(entries) == 1
        assert isinstance(entries[0], UnknownEntry)
        assert entries[0].content == ""
        _ = client.pop_api_call()
        client.clear_api_calls()

    def test_page_entries_use_caption_when_attachment_data_is_nil(
        self, client, notebook_tree: Notebook
    ):
        """Test attachment captions replace nil entry data."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        client.clear_api_calls()
        client.api_response = client.entries_response(
            client.xml(
                "entry",
                client.xml("eid", "attachment-1"),
                client.xml("part-type", "Attachment"),
                client.xml("entry-data", nil="true"),
                client.xml("caption", "Data file"),
            ),
            include_response=False,
        )

        entries = page.entries

        assert len(entries) == 1
        attachment_entry = entries[0]
        assert isinstance(attachment_entry, AttachmentEntry)
        assert attachment_entry.caption == "Data file"
        _ = client.pop_api_call()
        client.clear_api_calls()

    def test_page_entries_preserve_widget_entry_without_warning(
        self, client, notebook_tree: Notebook
    ):
        """Test widget entries load as WidgetEntry without fallback warnings."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        client.clear_api_calls()

        client.api_response = client.entries_response(
            client.entry_xml(
                "entry_widget",
                part_type="widget entry",
                entry_data='{"kind":"widget"}',
            ),
            include_response=False,
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            entries = page.entries

        assert len(entries) == 1
        assert type(entries[0]) is WidgetEntry
        assert entries[0].content_type == "widget entry"
        assert entries[0].content == '{"kind":"widget"}'
        assert caught == []
        _ = client.pop_api_call()
        client.clear_api_calls()

    def test_page_refresh(self, client, notebook_tree: Notebook):
        """Test NotebookPage.refresh clears cached entries."""
        page = notebook_tree[Index.Id : "page-1"]

        assert isinstance(page, NotebookPage)
        client.clear_api_calls()

        client.api_response = client.entries_response(
            client.entry_xml(
                "entry_1",
                part_type="text entry",
                entry_data="<p>Old</p>",
            ),
            include_response=False,
        )

        entries1 = page.entries
        assert len(entries1) == 1
        _ = client.pop_api_call()  # consume the load call

        page.refresh()

        client.api_response = client.entries_response(
            client.entry_xml(
                "entry_2",
                part_type="heading",
                entry_data="<h1>New</h1>",
            ),
            client.entry_xml(
                "entry_3",
                part_type="text entry",
                entry_data="<p>New2</p>",
            ),
            include_response=False,
        )

        entries2 = page.entries
        assert len(entries2) == 2
        assert entries1 is not entries2

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/get_entries_for_page"
        client.clear_api_calls()
