"""Custom exception types raised by ``labapi``."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from labapi.entry.entries.base import Entry


class LabArchivesError(Exception):
    """Base for all ``labapi`` exceptions."""


class AuthenticationError(LabArchivesError):
    """Missing credentials or failed authentication flow.

    ``error_code`` is set when the error originates from the LabArchives API
    (e.g. 4506 invalid akid, 4514 bad login, 4520 bad signature, 4533 session
    timeout).  It is ``None`` for locally-detected credential errors.
    """

    def __init__(self, message: str, error_code: int | None = None) -> None:
        """Initialize an authentication error."""
        super().__init__(message)
        self.error_code = error_code


class ApiError(LabArchivesError):
    """LabArchives API returned an error or unexpected response.

    ``error_code`` is the numeric code from the API ``<error-code>`` element,
    or ``None`` if the error was detected before parsing the response body.
    """

    def __init__(self, message: str, error_code: int | None = None) -> None:
        """Initialize an API error."""
        super().__init__(message)
        self.error_code = error_code


class NodeExistsError(LabArchivesError):
    """A tree node with the given name already exists (raised by InsertBehavior.Raise)."""


class PathError(LabArchivesError):
    """Path construction or resolution failed."""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        parent: str | None = None,
    ) -> None:
        """Initialize a path error with optional path context."""
        super().__init__(message)
        self.path = path
        self.parent = parent


class TraversalError(LabArchivesError):
    """Tree traversal failed."""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        segment: str | None = None,
        parent: str | None = None,
        available_children: list[str] | None = None,
    ) -> None:
        """Initialize a traversal error with optional path context."""
        super().__init__(message)
        self.path = path
        self.segment = segment
        self.parent = parent
        self.available_children = available_children


class ExtractionError(LabArchivesError, ValueError):
    """Structured parse/extraction failure while reading XML data."""


class TreeChildParseError(ExtractionError):
    """A tree child node could not be parsed from a tree-level response."""


class PartialEntryCreateError(LabArchivesError):
    """An entry was partially created but subsequent operations failed.

    ``partial_entry`` contains the successfully created entry object, which
    has already been added to the local collection and remote server.
    """

    def __init__(self, message: str, partial_entry: "Entry[Any]") -> None:
        """Initialize a partial entry create error."""
        super().__init__(message)
        self.partial_entry = partial_entry
