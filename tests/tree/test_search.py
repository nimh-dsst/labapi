"""Unit tests for EntrySearch pagination."""

from __future__ import annotations

import pytest
from lxml.etree import fromstring

from labapi.entry import AttachmentEntry
from labapi.tree.search import EntrySearch, EntrySearchPage


def _search_response(*, total_found: int, total_returned: int) -> object:
    """Build a minimal entry-search XML response."""
    return fromstring(
        f"<response>"
        f"<results>"
        f"<total-found type='integer'>{total_found}</total-found>"
        f"<total-returned type='integer'>{total_returned}</total-returned>"
        f"</results>"
        f"<entries/>"
        f"</response>"
    )


def _make_search(
    returned_by_page: list[int], *, page_size: int = 2, total_found: int | None = None
) -> EntrySearch:
    """Build an EntrySearch backed by a fake notebook/user.

    ``returned_by_page`` maps page_number -> how many results that page returns.
    ``total_found`` defaults to the sum of all entries across all pages.
    """
    if total_found is None:
        total_found = sum(returned_by_page)

    class FakeUser:
        def __init__(self) -> None:
            self.calls: list[int] = []

        def api_get(self, _method: str, *, page_number: int, **_kw: object) -> object:
            self.calls.append(page_number)
            returned = (
                returned_by_page[page_number]
                if page_number < len(returned_by_page)
                else 0
            )
            return _search_response(total_found=total_found, total_returned=returned)

    class FakeNotebook:
        id = "nbid"

        def __init__(self) -> None:
            self.user = FakeUser()

    nb = FakeNotebook()
    return EntrySearch(nb, "q", page_size=page_size)  # type: ignore[arg-type]


class TestEntrySearchIteration:
    """Tests for EntrySearch.__iter__ and EntrySearch.page."""

    def test_full_pages_iterate_all_results(self) -> None:
        """Two full pages of 2 each -> both pages yielded."""
        search = _make_search([2, 2], page_size=2)
        pages = list(search)

        assert len(pages) == 2
        assert pages[0].page_number == 0
        assert pages[1].page_number == 1

    def test_overcount_empty_page_stops_cleanly(self) -> None:
        """total_found overcounts; empty trailing page ends iteration without crash.

        Regression for #216: page() raises IndexError when total_returned == 0
        on page > 0. __iter__ must catch that and stop cleanly.
        """
        search = _make_search([2, 0], total_found=4, page_size=2)
        pages = list(search)  # must not raise IndexError

        assert [p.page_number for p in pages] == [0]

    def test_empty_first_page_yields_nothing(self) -> None:
        """If the very first page is empty, yield nothing."""
        search = _make_search([0], page_size=2)
        pages = list(search)

        assert pages == []

    def test_page_method_returns_correct_fields(self) -> None:
        """page() returns an EntrySearchPage with expected metadata."""
        search = _make_search([3], page_size=5)
        result = search.page(0)

        assert isinstance(result, EntrySearchPage)
        assert result.page_number == 0
        assert result.page_size == 5
        assert result.total_returned == 3
        assert result.total_found == 3
        assert result.entries == ()

    def test_page_negative_index_raises(self) -> None:
        """page() must raise IndexError for negative page numbers."""
        search = _make_search([1], page_size=2)
        with pytest.raises(IndexError, match="non-negative"):
            search.page(-1)

    def test_page_out_of_range_raises(self) -> None:
        """page() must raise IndexError for out-of-range page numbers."""
        search = _make_search([2], page_size=2)
        with pytest.raises(IndexError, match="out of range"):
            search.page(1)

    def test_attachment_result_preserves_listing_filename(self) -> None:
        """Attachment search results retain their original filename metadata."""
        response = fromstring(
            "<response>"
            "<results><total-found type='integer'>1</total-found>"
            "<total-returned type='integer'>1</total-returned></results>"
            "<entries><entry><eid>eid_att</eid><part-type>Attachment</part-type>"
            "<caption>Caption</caption><attach-file-name>original.txt</attach-file-name>"
            "</entry></entries></response>"
        )

        class FakeUser:
            def api_get(self, _method: str, **_kw: object) -> object:
                return response

        class FakeNotebook:
            id = "nbid"
            user = FakeUser()

        result = EntrySearch(FakeNotebook(), "q", page_size=2).page(0)  # type: ignore[arg-type]

        assert len(result.entries) == 1
        attachment = result.entries[0]
        assert isinstance(attachment, AttachmentEntry)
        assert attachment._filename == "original.txt"  # pyright: ignore[reportPrivateUsage]

    @pytest.mark.parametrize(
        ("entry_data_xml", "expected"),
        [
            ("<entry-data>Data</entry-data>", "Data"),
            ("<entry-data nil='true'/>", "Caption"),
            ("<entry-data/>", "Caption"),
            ("", "Caption"),
        ],
    )
    def test_result_data_falls_back_to_caption(
        self, entry_data_xml: str, expected: str
    ) -> None:
        """Missing, empty, or nil entry data falls back to the caption."""
        response = fromstring(
            "<response>"
            "<results><total-found type='integer'>1</total-found>"
            "<total-returned type='integer'>1</total-returned></results>"
            "<entries><entry><eid>eid_att</eid><part-type>Attachment</part-type>"
            f"{entry_data_xml}<caption>Caption</caption>"
            "</entry></entries></response>"
        )

        class FakeUser:
            def api_get(self, _method: str, **_kw: object) -> object:
                return response

        class FakeNotebook:
            id = "nbid"
            user = FakeUser()

        result = EntrySearch(FakeNotebook(), "q", page_size=2).page(0)  # type: ignore[arg-type]

        attachment = result.entries[0]
        assert isinstance(attachment, AttachmentEntry)
        assert attachment.caption == expected
