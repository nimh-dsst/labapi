"""Base entry classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from inspect import isabstract
from typing import TYPE_CHECKING, Any, ClassVar, Generic, Protocol, TypeVar, cast

if TYPE_CHECKING:
    from labapi.user import User

T = TypeVar("T")


class _EntryFactory(Protocol):
    _is_meta: ClassVar[bool]

    def __call__(
        self,
        eid: str,
        data: str,
        user: User,
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int | None = None,
    ) -> Entry[Any]: ...


class _MetaEntryFactory(Protocol):
    _is_meta: ClassVar[bool]

    def __call__(
        self,
        eid: str,
        data: str,
        user: User,
        *,
        part_type: str,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int | None = None,
    ) -> Entry[Any]: ...


_entries_registry: dict[str, type[Entry[Any]]] = {}


class Entry(ABC, Generic[T]):
    """Abstract base class for all entry types on a LabArchives page.

    This class provides a common interface for different entry types such as
    text entries, headers, attachments, and widgets. It uses a generic type
    parameter `T` to represent the content type of the entry.

    LabArchives does not currently expose an API endpoint for deleting
    individual entries, so this class intentionally does not provide a
    ``delete()`` method.

    :param T: The type of content stored in the entry (e.g., str for text, Attachment for files).
    """

    _part_type: ClassVar[str]
    _is_meta: ClassVar[bool]

    @staticmethod
    def is_registered(part_type: str) -> bool:
        """Return whether an entry class is registered for ``part_type``.

        :param part_type: The LabArchives part type identifier to check.
        :returns: True if a class is registered for this part type, False otherwise.
        """
        return part_type in _entries_registry

    @staticmethod
    def class_of(part_type: str) -> type[Entry[Any]]:
        """Return the registered entry class for ``part_type``.

        :param part_type: The LabArchives part type identifier.
        :returns: The :class:`~labapi.entry.entries.base.Entry` subclass
                  registered for this part type.
        :raises KeyError: If no class is registered for the specified part type.
        """
        return _entries_registry[part_type]

    @staticmethod
    def from_part_type(
        part_type: str,
        eid: str,
        data: str,
        user: User,
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int | None = None,
    ) -> Entry[Any]:
        """Create an entry instance for a LabArchives part type.

        This method takes a part type string and returns the corresponding
        entry class instance when one is registered. Recognized-but-unimplemented
        part types resolve to :class:`~labapi.entry.entries.unimplemented.UnimplementedEntry`,
        while truly unknown part types fall back to
        :class:`~labapi.entry.entries.unknown.UnknownEntry`.

        :param part_type: The type of entry to create (e.g., "heading", "text entry",
                         "plain text entry", "attachment", "widget entry").
        :param eid: The unique ID of the entry.
        :param data: The entry data. For text-based entries, this is the text content.
                    For attachment entries, this is the caption.
        :param user: The authenticated user associated with this entry.
        :param created_at: When the entry was created, if supplied by the API.
        :param updated_at: When the entry was last updated, if supplied by the API.
        :param version: The entry's API version number, if supplied by the API.
        :returns: An entry instance of the appropriate type.
        """
        klass = _entries_registry.get(part_type)

        if klass is None:
            from .unknown import UnknownEntry

            return UnknownEntry(
                eid,
                data,
                user,
                part_type=part_type,
                created_at=created_at,
                updated_at=updated_at,
                version=version,
            )

        if klass._is_meta:
            return cast(_MetaEntryFactory, klass)(
                eid,
                data,
                user,
                part_type=part_type,
                created_at=created_at,
                updated_at=updated_at,
                version=version,
            )

        return cast(_EntryFactory, klass)(
            eid,
            data,
            user,
            created_at=created_at,
            updated_at=updated_at,
            version=version,
        )

    # TODO perms
    def __init__(
        self,
        eid: str,
        data: str,
        user: User,
        *,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int | None = None,
    ):
        """Initialize an entry.

        :param eid: The unique ID of the entry.
        :param data: The entry data or attachment caption.
        :param user: The authenticated user associated with this entry.
        :param created_at: When the entry was created, if supplied by the API.
        :param updated_at: When the entry was last updated, if supplied by the API.
        :param version: The entry's API version number, if supplied by the API.
        """
        super().__init__()
        self._id = eid
        self._data = data
        self._user = user
        self._created_at = created_at
        self._updated_at = updated_at
        self._version = version

    def __init_subclass__(
        cls,
        part_type: str = "",
        meta_part_types: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Register concrete entry subclasses by their LabArchives part type."""
        if not isabstract(cls) and part_type == "":
            raise TypeError(f"{cls.__name__} must define a part_type")

        cls._part_type = part_type
        cls._is_meta = False
        _entries_registry[part_type] = cls

        if meta_part_types is not None and len(meta_part_types) > 0:
            cls._is_meta = True
            for m_part_type in meta_part_types:
                _entries_registry[m_part_type] = cls

        super().__init_subclass__(**kwargs)

    @property
    def id(self) -> str:
        """Return the unique identifier of the entry.

        :returns: The entry's ID as a string.
        """
        return self._id

    @property
    def content_type(self) -> str:
        """Return the LabArchives content type identifier for this entry.

        :returns: A string representing the entry's type (e.g., "text entry", "Attachment").
        """
        return self._part_type

    @property
    def created_at(self) -> datetime | None:
        """Return when this entry was created, if supplied by the API."""
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        """Return when this entry was last updated, if supplied by the API."""
        return self._updated_at

    @property
    def version(self) -> int | None:
        """Return this entry's API version number, if supplied by the API."""
        return self._version

    @property
    @abstractmethod
    def content(self) -> T:
        """Return the entry content.

        The specific type of the content depends on the entry type
        (e.g., string for text entries, :class:`~labapi.entry.attachment.Attachment` for attachments).

        :returns: The content of the entry.
        """
        raise NotImplementedError

    @content.setter
    @abstractmethod
    def content(self, value: T) -> None:
        """Set the entry content.

        This operation typically updates the entry in LabArchives via an API call.

        :param value: The new content for the entry.
        """
        raise NotImplementedError
