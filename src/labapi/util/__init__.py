"""Utility Functions and Classes for LabArchives API Client.

This package provides various utility functions and classes used throughout
the LabArchives API client, including XML extraction, type conversions,
indexing mechanisms, and data structures for notebook initialization.
"""

from .browser import detect_default_browser
from .env import getenv
from .extract import extract_etree, to_bool
from .path import NotebookPath
from .types import (
    IdIndex,
    IdOrNameIndex,
    Index,
    InsertBehavior,
    JsonData,
    NameIndex,
    NotebookInit,
)

__all__ = [
    "IdIndex",
    "IdOrNameIndex",
    "Index",
    "InsertBehavior",
    "JsonData",
    "NameIndex",
    "NotebookInit",
    "NotebookPath",
    "detect_default_browser",
    "extract_etree",
    "getenv",
    "to_bool",
]
