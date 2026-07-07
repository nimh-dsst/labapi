"""Text-based Entry Classes Module.

This module defines various classes for text-based entries within LabArchives,
including a base class for common text entry functionalities and specific
implementations for plain text, rich text, and header entries.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from typing_extensions import override

from .base import Entry

if TYPE_CHECKING:
    from labapi.user import User


class PlainTextEntry(Entry[str], part_type="plain text entry"):
    """Represents a plain text entry on a LabArchives page.

    This class is used for entries containing unformatted, raw text.
    Additionally, it provides common functionalities for entries whose content is
    represented as a string, including methods for getting and setting the content.
    """

    def __init__(self, eid: str, data: str, user: User):
        """Initialize a plain-text entry.

        :param eid: The unique ID of the entry.
        :param data: The text content of the entry.
        :param user: The authenticated user.
        """
        super().__init__(eid, data, user)

    @property
    @override
    def content(self) -> str:
        """Return the entry text.

        :returns: The content of the entry as a string.
        """
        return self._data

    @content.setter
    @override
    def content(self, value: str) -> None:
        """Set the entry text.

        This operation updates the entry's content in LabArchives via an API call.

        :param value: The new text content for the entry.
        """
        if not isinstance(value, str):
            raise TypeError(f"content must be a str, got {type(value).__name__}")

        self._user.api_post("entries/update_entry", {"entry_data": value}, eid=self.id)

        self._data = value


class TextEntry(PlainTextEntry, part_type="text entry"):
    """Represents a rich text entry on a LabArchives page.

    This class is used for entries containing formatted text, typically HTML.
    """


class HeaderEntry(PlainTextEntry, part_type="heading"):
    """Represents a header entry on a LabArchives page.

    This class is used for entries that function as headings or titles within a page.
    """
