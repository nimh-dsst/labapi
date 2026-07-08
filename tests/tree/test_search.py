"""Unit tests for EntrySearch pagination."""

from __future__ import annotations

from lxml.etree import fromstring

from labapi.tree.search import EntrySearch, EntrySearchPage


def _make_search(returned_by_page: list[int], *, page_size: int = 2) -> EntrySearch:
    """Build an EntrySearch backed by a fake notebook/user.

    ``returned_by_page`` maps page_number → how many results that page returns.
    ``total_found`` is always the sum of all entries across all pages.
    """
    total = sum(returned_by_page)

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
            return fromstring(
                f"<response>"
                f"<results>"
                f"<total-found type='integer'>{total}</total-found>"
                f"<total-returned type='integer'>{returned}</total-returned>"
                f"</results>"
                f"<entries/>"
                f"</response>"
            )

    class FakeNotebook:
        id = "nbid"

        def __init__(self) -> None:
            self.user = FakeUser()

    nb = FakeNotebook()
    search = EntrySearch(nb, "q", page_size=page_size)  # type: ignore[arg-type]
    search._notebook = nb  # type: ignore[attr-defined]
    return search


class TestEntrySearchIteration:
    """Tests for EntrySearch.__iter__ and EntrySearch.page."""

    def test_full_pages_iterate_all_results(self) -> None:
        """Two full pages of 2 each → both pages yielded."""
        search = _make_search([2, 2], page_size=2)
        pages = list(search)

        assert len(pages) == 2
        assert pages[0].page_number == 0
        assert pages[1].page_number == 1

    def test_short_page_does_not_stop_early(self) -> None:
        """Three short pages of 1 each, page_size=2 → all three pages yielded.

        Regression for #216: the old code estimated returned_so_far as
        page_number * page_size + total_returned, which under-counted when any
        page was shorter than page_size.
        """
        search = _make_search([1, 1, 1], page_size=2)
        pages = list(search)

        assert [p.page_number for p in pages] == [0, 1, 2]
        assert search._notebook.user.calls == [0, 1, 2]  # type: ignore[attr-defined]

    def test_overcount_empty_page_stops_cleanly(self) -> None:
        """total_found overcounts; empty page ends iteration without IndexError.

        Regression for #216: the old code raised IndexError from page() when
        total_returned == 0 on page > 0, so __iter__'s stop condition never
        ran.
        """
        search = _make_search([2, 0, 1], page_size=2)
        pages = list(search)  # must not raise IndexError

        # page 0 returns 2 = total_found, so iteration stops after page 0
        assert [p.page_number for p in pages] == [0]

    def test_empty_first_page_yields_nothing(self) -> None:
        """If the very first page is empty, yield nothing."""
        search = _make_search([0], page_size=2)
        pages = list(search)

        assert pages == []
        assert search._notebook.user.calls == [0]  # type: ignore[attr-defined]

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
        import pytest

        search = _make_search([1], page_size=2)
        with pytest.raises(IndexError, match="non-negative"):
            search.page(-1)
