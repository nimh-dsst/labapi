"""Search result objects for LabArchives notebooks."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from labapi.entry import AttachmentEntry, Entry
from labapi.util import extract_etree

if TYPE_CHECKING:
    from .notebook import Notebook


@dataclass(frozen=True)
class EntrySearchPage:
    """One page of LabArchives entry search results."""

    page_size: int
    page_number: int
    total_found: int
    total_returned: int
    entries: tuple[Entry[Any], ...]


class EntrySearch:
    """Lazy entry search over a LabArchives notebook."""

    def __init__(self, notebook: Notebook, query: str, *, page_size: int):
        """Initialize a notebook entry search."""
        if page_size <= 0:
            raise ValueError("page_size must be positive")

        self._notebook = notebook
        self._query = query
        self._page_size = page_size

    def __iter__(self) -> Iterator[EntrySearchPage]:
        """Iterate through search result pages until all results are exhausted."""
        page_number = 0

        while True:
            try:
                page = self.page(page_number)
            except IndexError:
                return
            if page.total_returned == 0:
                return

            yield page

            returned_so_far = page.page_number * page.page_size + page.total_returned
            if returned_so_far >= page.total_found:
                return

            page_number += 1

    def page(self, page_number: int) -> EntrySearchPage:
        """Return one zero-based search result page.

        :raises IndexError: If ``page_number`` is negative or out of range.
        """
        if page_number < 0:
            raise IndexError("search page index must be non-negative")

        response = self._notebook.user.api_get(
            "search_tools/entry_search",
            nbid=self._notebook.id,
            query=self._query,
            page_size=self._page_size,
            page_number=page_number,
            entry_data=True,
        )
        result_counts = extract_etree(
            response,
            {"results": {"total-found": int, "total-returned": int}},
        )

        entries: list[Entry[Any]] = []
        for entry_element in response.findall("./entries/entry"):
            entry_fields = extract_etree(entry_element, {"eid": str, "part-type": str})

            entry_data = entry_element.find("./entry-data")
            caption = entry_element.find("./caption")

            data = ""
            if (
                entry_data is not None
                and entry_data.get("nil") != "true"
                and entry_data.text is not None
            ):
                data = entry_data.text
            elif (
                caption is not None
                and caption.get("nil") != "true"
                and caption.text is not None
            ):
                data = caption.text

            entry = Entry.from_part_type(
                entry_fields["part-type"],
                entry_fields["eid"],
                data,
                self._notebook.user,
            )
            if isinstance(entry, AttachmentEntry):
                entry._filename = entry_element.findtext("./attach-file-name") or None  # pyright: ignore[reportPrivateUsage]

            entries.append(entry)

        page = EntrySearchPage(
            page_size=self._page_size,
            page_number=page_number,
            total_found=result_counts["total-found"],
            total_returned=result_counts["total-returned"],
            entries=tuple(entries),
        )

        if page_number > 0 and page.total_returned == 0:
            raise IndexError(f"search page index {page_number} is out of range")

        return page
