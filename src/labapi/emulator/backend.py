"""SQLite-backed state for the LabArchives emulator."""

from __future__ import annotations

from pathlib import Path

from peewee import (
    BlobField,
    BooleanField,
    CharField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

from .records import (
    AttachmentRecord,
    EntryId,
    EntryRecord,
    NotebookId,
    NotebookRecord,
    TreeNodeId,
    TreeNodeRecord,
)


class EmulatorBackend:
    """SQLite-backed state container for the public LabArchives emulator."""

    def __init__(self, db_path: str = ":memory:") -> None:
        """Initialize a new emulator backend instance."""
        self.db_path = db_path
        self.db = SqliteDatabase(db_path, pragmas={"foreign_keys": 1})
        self._init_models()
        self.connect()
        self._create_tables()

    def _init_models(self) -> None:
        """Bind peewee models to this backend's SQLite database."""
        if self.db_path != ":memory:":
            Path(self.db_path).expanduser().parent.mkdir(parents=True, exist_ok=True)

        database = self.db

        class BaseModel(Model):
            class Meta:
                database = database

        class NotebookModel(BaseModel):
            id = CharField(primary_key=True)
            name = TextField()
            is_default = BooleanField(default=False)

        class TreeNodeModel(BaseModel):
            tree_id = CharField(primary_key=True)
            notebook = ForeignKeyField(NotebookModel, backref="tree_nodes")
            parent_tree = ForeignKeyField(
                "self",
                backref="children",
                null=True,
                on_delete="CASCADE",
            )
            display_text = TextField()
            is_page = BooleanField()
            position = IntegerField(default=0)

        class EntryModel(BaseModel):
            eid = CharField(primary_key=True)
            page = ForeignKeyField(
                TreeNodeModel, backref="entries", on_delete="CASCADE"
            )
            part_type = TextField()
            entry_data = TextField()
            attach_file_name = TextField(default="")
            attach_content_type = TextField(default="")
            position = IntegerField(default=0)

        class AttachmentModel(BaseModel):
            entry = ForeignKeyField(
                EntryModel,
                backref="attachment_rows",
                unique=True,
                on_delete="CASCADE",
            )
            filename = TextField()
            mime_type = TextField()
            content = BlobField()

        self._NotebookModel = NotebookModel
        self._TreeNodeModel = TreeNodeModel
        self._EntryModel = EntryModel
        self._AttachmentModel = AttachmentModel
        self._tables = (
            NotebookModel,
            TreeNodeModel,
            EntryModel,
            AttachmentModel,
        )

    def _create_tables(self) -> None:
        """Create the emulator schema if it does not already exist."""
        self.db.create_tables(self._tables, safe=True)

    def connect(self) -> None:
        """Open the emulator database connection if needed."""
        self.db.connect(reuse_if_open=True)

    def close(self) -> None:
        """Close the emulator database connection if it is open."""
        if not self.db.is_closed():
            self.db.close()

    def reset(self) -> None:
        """Clear all emulator data and recreate the schema."""
        self.connect()
        self.db.drop_tables(self._tables, safe=True)
        self._create_tables()

    @property
    def notebooks(self) -> list[NotebookRecord]:
        """Return all notebooks as public record objects."""
        return self.list_notebooks()

    @property
    def tree_nodes(self) -> list[TreeNodeRecord]:
        """Return all tree nodes as public record objects."""
        return self.list_tree_nodes()

    @property
    def entries(self) -> list[EntryRecord]:
        """Return all entries as public record objects."""
        return self.list_entries()

    @property
    def attachments(self) -> list[AttachmentRecord]:
        """Return all attachments as public record objects."""
        return self.list_attachments()

    def next_id(self, kind: str) -> str:
        """Generate the next unused identifier for a record kind."""
        stores = {
            "notebook": (self._NotebookModel, "nb", "id"),
            "directory": (self._TreeNodeModel, "dir", "tree_id"),
            "page": (self._TreeNodeModel, "page", "tree_id"),
            "entry": (self._EntryModel, "eid", "eid"),
        }
        model_info = stores.get(kind)
        if model_info is None:
            raise ValueError(f"Unknown counter kind: {kind}")

        model, prefix, field_name = model_info
        counter = model.select().count() + 1
        while True:
            candidate = f"{prefix}{counter}"
            if model.get_or_none(getattr(model, field_name) == candidate) is None:
                return candidate
            counter += 1

    def add_notebook(
        self,
        name: str,
        *,
        notebook_id: NotebookId | str | None = None,
        is_default: bool = False,
    ) -> NotebookRecord:
        """Create and persist a notebook record."""
        row = self._NotebookModel.create(
            id=str(notebook_id or self.next_id("notebook")),
            name=name,
            is_default=is_default,
        )
        return self._notebook_record(row)

    def add_tree_node(
        self,
        display_text: str,
        *,
        notebook_id: NotebookId | str,
        is_page: bool,
        tree_id: TreeNodeId | str | None = None,
        parent_tree_id: TreeNodeId | str | None = None,
    ) -> TreeNodeRecord:
        """Create and persist a directory or page record."""
        notebook = self._require_notebook_row(notebook_id)
        parent = None
        if parent_tree_id is not None:
            parent = self._require_tree_node_row(parent_tree_id)

        row = self._TreeNodeModel.create(
            tree_id=str(tree_id or self.next_id("page" if is_page else "directory")),
            notebook=notebook,
            parent_tree=parent,
            display_text=display_text,
            is_page=is_page,
            position=self._next_tree_position(notebook.id, parent_tree_id),
        )
        return self._tree_node_record(row)

    def add_entry(
        self,
        part_type: str,
        entry_data: str,
        *,
        page_tree_id: TreeNodeId | str,
        entry_id: EntryId | str | None = None,
        attach_file_name: str = "",
        attach_content_type: str = "",
    ) -> EntryRecord:
        """Create and persist an entry on a page."""
        page = self._require_tree_node_row(page_tree_id)
        if not page.is_page:
            raise ValueError(f"Tree node {page_tree_id} is not a page")

        row = self._EntryModel.create(
            eid=str(entry_id or self.next_id("entry")),
            page=page,
            part_type=part_type,
            entry_data=entry_data,
            attach_file_name=attach_file_name,
            attach_content_type=attach_content_type,
            position=self._next_entry_position(page.tree_id),
        )
        return self._entry_record(row)

    def set_attachment(
        self,
        entry_id: EntryId | str,
        *,
        filename: str,
        mime_type: str,
        content: bytes,
    ) -> AttachmentRecord:
        """Create or replace an attachment payload for an entry."""
        entry = self._require_entry_row(entry_id)
        self._AttachmentModel.replace(
            entry=entry,
            filename=filename,
            mime_type=mime_type,
            content=content,
        ).execute()
        return AttachmentRecord(filename, mime_type, content)

    def get_notebook(self, notebook_id: NotebookId | str) -> NotebookRecord | None:
        """Return a notebook by id if it exists."""
        row = self._NotebookModel.get_or_none(
            self._NotebookModel.id == str(notebook_id)
        )
        return None if row is None else self._notebook_record(row)

    def get_tree_node(self, tree_id: TreeNodeId | str) -> TreeNodeRecord | None:
        """Return a tree node by id if it exists."""
        row = self._TreeNodeModel.get_or_none(
            self._TreeNodeModel.tree_id == str(tree_id)
        )
        return None if row is None else self._tree_node_record(row)

    def get_entry(self, entry_id: EntryId | str) -> EntryRecord | None:
        """Return an entry by id if it exists."""
        row = self._EntryModel.get_or_none(self._EntryModel.eid == str(entry_id))
        return None if row is None else self._entry_record(row)

    def get_attachment(self, entry_id: EntryId | str) -> AttachmentRecord | None:
        """Return an attachment payload by entry id if it exists."""
        row = self._AttachmentModel.get_or_none(
            self._AttachmentModel.entry == str(entry_id)
        )
        return (
            None
            if row is None
            else AttachmentRecord(
                row.filename,
                row.mime_type,
                row.content,
            )
        )

    def list_notebooks(self) -> list[NotebookRecord]:
        """Return all notebooks."""
        return [
            self._notebook_record(row)
            for row in self._NotebookModel.select().order_by(self._NotebookModel.id)
        ]

    def list_tree_nodes(self) -> list[TreeNodeRecord]:
        """Return all tree nodes."""
        return [
            self._tree_node_record(row)
            for row in self._TreeNodeModel.select().order_by(
                self._TreeNodeModel.notebook,
                self._TreeNodeModel.parent_tree,
                self._TreeNodeModel.position,
                self._TreeNodeModel.tree_id,
            )
        ]

    def list_entries(
        self, *, page_tree_id: TreeNodeId | str | None = None
    ) -> list[EntryRecord]:
        """Return all entries, optionally filtered to a page."""
        query = self._EntryModel.select()
        if page_tree_id is not None:
            query = query.where(self._EntryModel.page == str(page_tree_id))
        return [
            self._entry_record(row)
            for row in query.order_by(self._EntryModel.page, self._EntryModel.position)
        ]

    def list_attachments(self) -> list[AttachmentRecord]:
        """Return all attachment payloads."""
        return [
            AttachmentRecord(row.filename, row.mime_type, row.content)
            for row in self._AttachmentModel.select().order_by(self._AttachmentModel.id)
        ]

    def children_of_root(self, notebook_id: NotebookId | str) -> list[TreeNodeRecord]:
        """Return the root-level tree nodes for a notebook."""
        notebook = self._require_notebook_row(notebook_id)
        return [
            self._tree_node_record(row)
            for row in self._TreeNodeModel.select()
            .where(
                (self._TreeNodeModel.notebook == notebook)
                & self._TreeNodeModel.parent_tree.is_null()
            )
            .order_by(self._TreeNodeModel.position)
        ]

    def children_of_node(self, tree_id: TreeNodeId | str) -> list[TreeNodeRecord]:
        """Return direct child tree nodes for a directory."""
        parent = self._require_tree_node_row(tree_id)
        return [
            self._tree_node_record(row)
            for row in self._TreeNodeModel.select()
            .where(self._TreeNodeModel.parent_tree == parent)
            .order_by(self._TreeNodeModel.position)
        ]

    def entries_for_page(self, tree_id: TreeNodeId | str) -> list[EntryRecord]:
        """Return direct entries for a page."""
        page = self._require_tree_node_row(tree_id)
        return [
            self._entry_record(row)
            for row in self._EntryModel.select()
            .where(self._EntryModel.page == page)
            .order_by(self._EntryModel.position)
        ]

    def serve(
        self,
        *,
        host: str = "127.0.0.1",
        port: int = 8080,
        reload: bool = False,
        log_level: str = "info",
    ) -> None:
        """Run the emulator as a local FastAPI server."""
        from .server import serve

        serve(self, host=host, port=port, reload=reload, log_level=log_level)

    def _require_notebook_row(self, notebook_id: NotebookId | str) -> Model:
        row = self._NotebookModel.get_or_none(
            self._NotebookModel.id == str(notebook_id)
        )
        if row is None:
            raise KeyError(f"Notebook not found: {notebook_id}")
        return row

    def _require_tree_node_row(self, tree_id: TreeNodeId | str) -> Model:
        row = self._TreeNodeModel.get_or_none(
            self._TreeNodeModel.tree_id == str(tree_id)
        )
        if row is None:
            raise KeyError(f"Tree node not found: {tree_id}")
        return row

    def _require_entry_row(self, entry_id: EntryId | str) -> Model:
        row = self._EntryModel.get_or_none(self._EntryModel.eid == str(entry_id))
        if row is None:
            raise KeyError(f"Entry not found: {entry_id}")
        return row

    def _next_tree_position(
        self,
        notebook_id: NotebookId | str,
        parent_tree_id: TreeNodeId | str | None,
    ) -> int:
        notebook = self._require_notebook_row(notebook_id)
        query = self._TreeNodeModel.select(self._TreeNodeModel.position).where(
            self._TreeNodeModel.notebook == notebook
        )
        if parent_tree_id is None:
            query = query.where(self._TreeNodeModel.parent_tree.is_null())
        else:
            query = query.where(self._TreeNodeModel.parent_tree == str(parent_tree_id))
        last = query.order_by(self._TreeNodeModel.position.desc()).first()
        return 0 if last is None else last.position + 1

    def _next_entry_position(self, page_tree_id: TreeNodeId | str) -> int:
        query = self._EntryModel.select(self._EntryModel.position).where(
            self._EntryModel.page == str(page_tree_id)
        )
        last = query.order_by(self._EntryModel.position.desc()).first()
        return 0 if last is None else last.position + 1

    def _notebook_record(self, row: Model) -> NotebookRecord:
        child_ids = [
            child.tree_id
            for child in self._TreeNodeModel.select()
            .where(
                (self._TreeNodeModel.notebook == row)
                & self._TreeNodeModel.parent_tree.is_null()
            )
            .order_by(self._TreeNodeModel.position)
        ]
        return NotebookRecord(row.id, row.name, row.is_default, child_ids)

    def _tree_node_record(self, row: Model) -> TreeNodeRecord:
        if row.is_page:
            child_ids = [
                entry.eid
                for entry in self._EntryModel.select()
                .where(self._EntryModel.page == row)
                .order_by(self._EntryModel.position)
            ]
        else:
            child_ids = [
                child.tree_id
                for child in self._TreeNodeModel.select()
                .where(self._TreeNodeModel.parent_tree == row)
                .order_by(self._TreeNodeModel.position)
            ]
        return TreeNodeRecord(row.tree_id, row.display_text, row.is_page, child_ids)

    def _entry_record(self, row: Model) -> EntryRecord:
        return EntryRecord(
            row.eid,
            row.part_type,
            row.entry_data,
            attach_file_name=row.attach_file_name,
            attach_content_type=row.attach_content_type,
        )
