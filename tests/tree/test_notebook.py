"""Unit tests for Notebook class."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from labapi import (
    AttachmentEntry,
    Client,
    HeaderEntry,
    Notebook,
    NotebookPage,
    PlainTextEntry,
    TextEntry,
    UnknownEntry,
)
from labapi.tree.collection import Notebooks
from labapi.user import User
from labapi.util.types import NotebookInit


def search_response(client, *entries, total_found: int, total_returned: int):
    """Build an entry-search API response."""
    return client.xml(
        "search-tools",
        client.xml(
            "results",
            client.xml("total-found", total_found, type="integer"),
            client.xml("total-returned", total_returned, type="integer"),
        ),
        client.xml("entries", *entries, type="array"),
    )


class TestNotebookUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_notebook_properties(self):
        """Test Notebook stores id, name, is_default, and is its own root."""
        mock_user = Mock(spec=User)
        mock_notebooks = Mock(spec=Notebooks)

        init = NotebookInit(id="nb_test", name="Test Notebook", is_default=True)
        notebook = Notebook(init, mock_user, mock_notebooks)

        assert notebook.id == "nb_test"
        assert notebook.name == "Test Notebook"
        assert notebook.is_default is True
        assert notebook.root is notebook

    def test_notebook_and_page_urls(self):
        """Test notebooks and pages build Web UI URLs from their IDs."""
        with Client("https://api.labarchives-gov.com", "test", "test") as client:
            user = User("test-user", "test@example.com", [], client)
            notebook = Notebook(
                NotebookInit("notebook-token", "Test Notebook", False),
                user,
                user.notebooks,
            )
            page = NotebookPage("page-1", "Test Page", notebook, notebook, user)

            assert notebook.url == (
                "https://mynotebook.labarchives-gov.com/notebook-token"
            )
            assert page.url == (
                "https://mynotebook.labarchives-gov.com/notebook-token/page/page-1"
            )

    def test_search_is_lazy(self):
        """Test Notebook.search does not call the API until a page is requested."""
        mock_user = Mock(spec=User)
        mock_notebooks = Mock(spec=Notebooks)

        init = NotebookInit(id="nb_test", name="Test Notebook", is_default=True)
        notebook = Notebook(init, mock_user, mock_notebooks)

        _ = notebook.search("brown rat", page_size=50)

        mock_user.api_get.assert_not_called()


class TestNotebookIntegration:
    """Integration tests with real objects and mocked API."""

    def test_notebook_name_setter(self, client, notebook: Notebook):
        """Test Notebook.name setter updates name via API."""
        client.api_response = client.xml(
            "notebooks",
            client.xml("success", True),
        )

        notebook.name = "Updated Notebook Name"

        api_call = client.pop_api_call()
        assert api_call[0] == "notebooks/modify_notebook_info"
        assert api_call[1]["nbid"] == "testnb1"
        assert api_call[1]["name"] == "Updated Notebook Name"
        assert notebook.name == "Updated Notebook Name"

    def test_search_page_returns_entries(self, client, notebook: Notebook):
        """Test entry search calls the search endpoint and returns entry objects."""
        client.api_response = search_response(
            client,
            client.xml(
                "entry",
                client.xml("eid", "text-1"),
                client.xml("part-type", "text entry"),
                client.xml("entry-data", "<p>brown rat</p>"),
            ),
            client.xml(
                "entry",
                client.xml("eid", "header-1"),
                client.xml("part-type", "heading"),
                client.xml("entry-data", "Results"),
            ),
            client.xml(
                "entry",
                client.xml("eid", "plain-1"),
                client.xml("part-type", "plain text entry"),
                client.xml("entry-data", "notes"),
            ),
            client.xml(
                "entry",
                client.xml("eid", "attachment-1"),
                client.xml("part-type", "Attachment"),
                client.xml("caption", "data file"),
            ),
            client.xml(
                "entry",
                client.xml("eid", "future-1"),
                client.xml("part-type", "future entry"),
                client.xml("entry-data", "payload"),
            ),
            total_found=5,
            total_returned=5,
        )

        page = notebook.search("brown rat", page_size=10).page(0)

        api_call = client.pop_api_call()
        assert api_call[0] == "search_tools/entry_search"
        assert api_call[1] == {
            "uid": "testid1",
            "nbid": "testnb1",
            "query": "brown rat",
            "page_size": 10,
            "page_number": 0,
            "entry_data": True,
        }
        assert page.page_size == 10
        assert page.page_number == 0
        assert page.total_found == 5
        assert page.total_returned == 5
        text_entry = page.entries[0]
        header_entry = page.entries[1]
        plain_text_entry = page.entries[2]
        attachment_entry = page.entries[3]
        unknown_entry = page.entries[4]
        assert isinstance(text_entry, TextEntry)
        assert isinstance(header_entry, HeaderEntry)
        assert isinstance(plain_text_entry, PlainTextEntry)
        assert isinstance(attachment_entry, AttachmentEntry)
        assert isinstance(unknown_entry, UnknownEntry)
        assert text_entry.content == "<p>brown rat</p>"
        assert attachment_entry.caption == "data file"

    def test_search_result_entries_use_existing_update_endpoint(
        self, client, notebook: Notebook
    ):
        """Test search results are normal entries that update by entry id."""
        client.api_response = search_response(
            client,
            client.xml(
                "entry",
                client.xml("eid", "text-1"),
                client.xml("part-type", "text entry"),
                client.xml("entry-data", "<p>brown rat</p>"),
            ),
            total_found=1,
            total_returned=1,
        )

        entry = notebook.search("brown rat").page(0).entries[0]
        _ = client.pop_api_call()

        assert isinstance(entry, TextEntry)
        client.api_response = client.xml("entries", client.xml("success", True))

        entry.content = entry.content.replace("brown rat", "Rattus norvegicus")

        api_call = client.pop_api_call()
        assert api_call[0] == "entries/update_entry"
        assert api_call[1]["uid"] == "testid1"
        assert api_call[1]["eid"] == "text-1"
        assert api_call[1]["entry_data"] == "<p>Rattus norvegicus</p>"

    def test_search_iteration_fetches_pages(self, client, notebook: Notebook):
        """Test entry search iteration follows result pages until complete."""
        client.api_response = search_response(
            client,
            client.xml(
                "entry",
                client.xml("eid", "text-1"),
                client.xml("part-type", "text entry"),
                client.xml("entry-data", "first"),
            ),
            client.xml(
                "entry",
                client.xml("eid", "text-2"),
                client.xml("part-type", "text entry"),
                client.xml("entry-data", "second"),
            ),
            total_found=3,
            total_returned=2,
        )
        client.api_response = search_response(
            client,
            client.xml(
                "entry",
                client.xml("eid", "text-3"),
                client.xml("part-type", "text entry"),
                client.xml("entry-data", "third"),
            ),
            total_found=3,
            total_returned=1,
        )

        pages = list(notebook.search("brown rat", page_size=2))

        first_call = client.pop_api_call()
        second_call = client.pop_api_call()
        assert first_call[1]["page_number"] == 0
        assert second_call[1]["page_number"] == 1
        assert [page.page_number for page in pages] == [0, 1]
        assert [entry.id for page in pages for entry in page.entries] == [
            "text-1",
            "text-2",
            "text-3",
        ]

    def test_search_page_zero_can_be_empty(self, client, notebook: Notebook):
        """Test the first search page can represent an empty result set."""
        client.api_response = search_response(
            client,
            total_found=0,
            total_returned=0,
        )

        page = notebook.search("missing").page(0)

        _ = client.pop_api_call()
        assert page.page_number == 0
        assert page.total_found == 0
        assert page.total_returned == 0
        assert page.entries == ()

    def test_search_iteration_does_not_yield_empty_first_page(
        self, client, notebook: Notebook
    ):
        """Test search iteration stops without yielding when no entries match."""
        client.api_response = search_response(
            client,
            total_found=0,
            total_returned=0,
        )

        pages = list(notebook.search("missing"))

        _ = client.pop_api_call()
        assert pages == []

    def test_search_page_negative_index_raises(self, notebook: Notebook):
        """Test search page indexes are non-negative."""
        with pytest.raises(IndexError, match="non-negative"):
            notebook.search("brown rat").page(-1)

    def test_search_page_out_of_range_raises(self, client, notebook: Notebook):
        """Test explicit search page access raises when the page is out of range."""
        client.api_response = search_response(
            client,
            total_found=1,
            total_returned=0,
        )

        with pytest.raises(IndexError, match="out of range"):
            notebook.search("brown rat").page(1)

        _ = client.pop_api_call()
