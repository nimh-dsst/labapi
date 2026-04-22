"""Record types used by the LabArchives emulator."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import NewType, cast

NotebookId = NewType("NotebookId", str)
TreeNodeId = NewType("TreeNodeId", str)
EntryId = NewType("EntryId", str)


@dataclass(init=False, slots=True)
class NotebookRecord:
    """Stored notebook state for the emulator."""

    id: NotebookId
    name: str
    is_default: bool = False
    child_ids: list[TreeNodeId] = field(default_factory=list)

    def __init__(
        self,
        _id: NotebookId | str,
        name: str,
        is_default: bool = False,
        child_ids: Sequence[TreeNodeId | str] = (),
    ) -> None:
        """Initialize a notebook record."""
        self.id = NotebookId(_id)
        self.name = name
        self.is_default = is_default
        self.child_ids = [TreeNodeId(child_id) for child_id in child_ids]

    def to_xml(self) -> str:
        """Serialize this notebook as canonical emulator XML."""
        from .xml import render_notebook

        return render_notebook(self)


@dataclass(init=False, slots=True)
class TreeNodeRecord:
    """Stored tree node state for the emulator."""

    tree_id: TreeNodeId
    display_text: str
    is_page: bool
    child_ids: list[TreeNodeId | EntryId] = field(default_factory=list)

    def __init__(
        self,
        tree_id: TreeNodeId | str,
        display_text: str,
        is_page: bool,
        child_ids: Sequence[TreeNodeId | EntryId | str] = (),
    ) -> None:
        """Initialize a tree node record."""
        self.tree_id = TreeNodeId(tree_id)
        self.display_text = display_text
        self.is_page = is_page
        self.child_ids = [
            cast(TreeNodeId | EntryId, child_id) for child_id in child_ids
        ]

    def to_xml(self, *, tag: str = "node") -> str:
        """Serialize this tree node as canonical emulator XML."""
        from .xml import render_tree_node

        return render_tree_node(self, tag=tag)


@dataclass(init=False, slots=True)
class EntryRecord:
    """Stored entry state for the emulator."""

    eid: EntryId
    part_type: str
    entry_data: str
    attach_file_name: str = ""
    attach_content_type: str = ""

    def __init__(
        self,
        eid: EntryId | str,
        part_type: str,
        entry_data: str,
        attach_file_name: str = "",
        attach_content_type: str = "",
    ) -> None:
        """Initialize an entry record."""
        self.eid = EntryId(eid)
        self.part_type = part_type
        self.entry_data = entry_data
        self.attach_file_name = attach_file_name
        self.attach_content_type = attach_content_type

    def to_xml(self) -> str:
        """Serialize this entry as canonical emulator XML."""
        from .xml import render_entry

        return render_entry(self)


@dataclass(slots=True)
class AttachmentRecord:
    """Stored attachment payload for an attachment entry."""

    filename: str
    mime_type: str
    content: bytes
