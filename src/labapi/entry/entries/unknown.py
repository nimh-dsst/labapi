"""Entry fallback types."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from typing_extensions import override

from .base import Entry

if TYPE_CHECKING:
    from labapi.user import User

_UNKNOWN_ENTRY_REGISTRY_SENTINEL = "__labapi_internal_unknown_entry__"
_UNIMPLEMENTED_ENTRY_REGISTRY_SENTINEL = "__labapi_internal_unimplemented_entry__"


class UnknownEntry(Entry[str], part_type=_UNKNOWN_ENTRY_REGISTRY_SENTINEL):
    """Fallback entry wrapper for unknown upstream part types."""

    def __init__(
        self,
        eid: str,
        data: str,
        user: User,
        *,
        part_type: str,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int | None = None,
    ):
        """Initialize an unknown entry wrapper."""
        super().__init__(
            eid,
            data,
            user,
            created_at=created_at,
            updated_at=updated_at,
            version=version,
        )
        self._source_part_type = part_type

    @property
    @override
    def content_type(self) -> str:
        """Return the original upstream part type."""
        return self._source_part_type

    @property
    @override
    def content(self) -> str:
        """Return the raw entry payload."""
        return self._data

    @content.setter
    @override
    def content(self, value: str) -> None:
        """Reject updates for unsupported entry types."""
        raise NotImplementedError(
            f"Cannot update unsupported entry type '{self._source_part_type}'"
        )


class UnimplementedEntry(
    UnknownEntry,
    part_type=_UNIMPLEMENTED_ENTRY_REGISTRY_SENTINEL,
    meta_part_types={
        "sketch entry",
        "equation entry",
        "reference entry",
        "assignment entry",
    },
):
    """Fallback entry wrapper for known upstream part types not yet implemented."""

    @UnknownEntry.content.setter  # type: ignore[attr-defined]
    @override
    def content(self, value: str) -> None:
        """Reject updates for recognized-but-unimplemented entry types."""
        raise NotImplementedError(
            f"Cannot update unimplemented entry type '{self._source_part_type}'"
        )
