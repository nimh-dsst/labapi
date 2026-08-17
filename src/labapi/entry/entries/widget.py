"""Widget Entry Module.

This module defines the :class:`~labapi.entry.entries.widget.WidgetEntry` class,
which represents a widget entry within a LabArchives page.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from .unknown import UnimplementedEntry

if TYPE_CHECKING:
    from labapi.user import User


class WidgetEntry(UnimplementedEntry, part_type="widget entry"):
    """Backward-compatible widget entry alias using unimplemented behavior."""

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
        """Initialize a widget entry as an unimplemented entry wrapper."""
        super().__init__(
            eid,
            data,
            user,
            part_type="widget entry",
            created_at=created_at,
            updated_at=updated_at,
            version=version,
        )
