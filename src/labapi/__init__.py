"""LabArchives API Client Library.

This package provides a Python client for interacting with the LabArchives API.
It offers an object-oriented interface to manage notebooks, folders, pages,
and various entry types, along with authentication and utility functions.

Key components include:

- :class:`~labapi.client.Client`: The main API client for connection and authentication.
- :class:`~labapi.user.User`: Represents an authenticated user session.
- :mod:`~labapi.tree`: Modules for managing the hierarchical tree structure (notebooks, directories, pages).
- :mod:`~labapi.entry`: Modules for handling different types of entries within pages.
- :mod:`~labapi.util`: General utility functions and data structures.
"""

from importlib.metadata import PackageNotFoundError, version

from .client import Client
from .entry import (
    Attachment,
    AttachmentEntry,
    Entry,
    HeaderEntry,
    PlainTextEntry,
    TextEntry,
    UnimplementedEntry,
    UnknownEntry,
    WidgetEntry,
)
from .exceptions import (
    ApiError,
    AuthenticationError,
    ExtractionError,
    LabArchivesError,
    NodeExistsError,
    PartialEntryCreateError,
    PathError,
    TraversalError,
    TreeChildParseError,
)
from .tree import (
    AbstractTreeContainer,
    Notebook,
    NotebookDirectory,
    NotebookPage,
)
from .user import User
from .util import Index, InsertBehavior, JsonData, NotebookPath

try:
    __version__ = version("labapi")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = [
    "AbstractTreeContainer",
    "ApiError",
    "Attachment",
    "AttachmentEntry",
    "AuthenticationError",
    "Client",
    "Entry",
    "ExtractionError",
    "HeaderEntry",
    "Index",
    "InsertBehavior",
    "JsonData",
    "LabArchivesError",
    "NodeExistsError",
    "Notebook",
    "NotebookDirectory",
    "NotebookPage",
    "NotebookPath",
    "PartialEntryCreateError",
    "PathError",
    "PlainTextEntry",
    "TextEntry",
    "TraversalError",
    "TreeChildParseError",
    "UnimplementedEntry",
    "UnknownEntry",
    "User",
    "WidgetEntry",
    "__version__",
]
