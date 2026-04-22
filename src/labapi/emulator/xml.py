"""xsdata-backed XML serializers for emulator records."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from .records import EntryRecord, NotebookRecord, TreeNodeRecord


@dataclass
class _NotebookXml:
    class Meta:
        name = "notebook"

    is_default: bool = field(metadata={"name": "is-default", "type": "Element"})
    name: str = field(metadata={"type": "Element"})
    id: str = field(metadata={"type": "Element"})


@dataclass
class _NodeXml:
    class Meta:
        name = "node"

    is_page: bool = field(metadata={"name": "is-page", "type": "Element"})
    tree_id: str = field(metadata={"name": "tree-id", "type": "Element"})
    display_text: str = field(metadata={"name": "display-text", "type": "Element"})


@dataclass
class _LevelNodeXml:
    class Meta:
        name = "level-node"

    is_page: bool = field(metadata={"name": "is-page", "type": "Element"})
    tree_id: str = field(metadata={"name": "tree-id", "type": "Element"})
    display_text: str = field(metadata={"name": "display-text", "type": "Element"})


@dataclass
class _EntryXml:
    class Meta:
        name = "entry"

    eid: str = field(metadata={"type": "Element"})
    part_type: str = field(metadata={"name": "part-type", "type": "Element"})
    attach_file_name: str = field(
        metadata={"name": "attach-file-name", "type": "Element"}
    )
    attach_content_type: str = field(
        metadata={"name": "attach-content-type", "type": "Element"}
    )
    entry_data: str = field(metadata={"name": "entry-data", "type": "Element"})


@lru_cache(maxsize=1)
def _serializer() -> Any:
    """Create the shared xsdata serializer on first use."""
    try:
        from xsdata.formats.dataclass.serializers import XmlSerializer
        from xsdata.formats.dataclass.serializers.config import SerializerConfig
    except ImportError as exc:  # pragma: no cover - dependency boundary
        raise RuntimeError(
            "xsdata is required for emulator XML serialization. "
            "Install labapi[emulator]."
        ) from exc

    return XmlSerializer(config=SerializerConfig(xml_declaration=False))


def _render(binding: object) -> str:
    """Render an xsdata binding object to XML text."""
    return _serializer().render(binding)


def render_notebook(record: NotebookRecord) -> str:
    """Render a notebook record as canonical notebook XML."""
    return _render(
        _NotebookXml(
            is_default=record.is_default,
            name=record.name,
            id=record.id,
        )
    )


def render_tree_node(record: TreeNodeRecord, *, tag: str = "node") -> str:
    """Render a tree node record as canonical node XML."""
    if tag == "node":
        binding: object = _NodeXml(
            is_page=record.is_page,
            tree_id=record.tree_id,
            display_text=record.display_text,
        )
    elif tag == "level-node":
        binding = _LevelNodeXml(
            is_page=record.is_page,
            tree_id=record.tree_id,
            display_text=record.display_text,
        )
    else:
        raise ValueError(f"Unsupported tree node tag: {tag}")
    return _render(binding)


def render_entry(record: EntryRecord) -> str:
    """Render an entry record as canonical entry XML."""
    return _render(
        _EntryXml(
            eid=record.eid,
            part_type=record.part_type,
            attach_file_name=record.attach_file_name,
            attach_content_type=record.attach_content_type,
            entry_data=record.entry_data,
        )
    )
