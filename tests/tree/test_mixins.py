"""Unit tests for tree mixins."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, cast

import pytest

from labapi import Index, Notebook, NotebookDirectory, NotebookPage
from labapi.exceptions import (
    NodeExistsError,
    PathError,
    TraversalError,
    TreeChildParseError,
)
from labapi.tree.mixins import (
    AbstractTreeContainer,
)
from labapi.util import InsertBehavior, NotebookPath
from labapi.util.path import EscapedSegment


def expect_dir(node: object) -> NotebookDirectory:
    """Narrow a dynamically-returned tree node to NotebookDirectory."""
    assert isinstance(node, NotebookDirectory)
    return node


def expect_page(node: object) -> NotebookPage:
    """Narrow a dynamically-returned tree node to NotebookPage."""
    assert isinstance(node, NotebookPage)
    return node


class TestTreeMixinsIntegration:
    """Integration tests for mixin functionality using the notebook tree fixture."""

    def test_traverse_relative(self, notebook_tree: Notebook):
        """Test traversing with relative paths."""
        folder_a = notebook_tree.traverse("Test Folder A")
        assert folder_a.name == "Test Folder A"
        assert folder_a.id == "dir-1"

        page_a = folder_a.traverse("Dir1 Test Page A")
        assert page_a.name == "Dir1 Test Page A"
        assert page_a.id == "page-1-1"

    def test_traverse_absolute(self, notebook_tree: Notebook):
        """Test traversing with absolute paths."""
        page_a = notebook_tree.traverse("/Test Folder A/Dir1 Test Page A")
        assert page_a.name == "Dir1 Test Page A"
        assert page_a.id == "page-1-1"

    def test_traverse_escaped_separator_in_node_names(self, notebook_tree: Notebook):
        """Test traversing to nodes whose names contain literal slashes."""
        slash_dir = NotebookDirectory(
            "slash-dir",
            "Reports/2024",
            notebook_tree,
            notebook_tree,
            notebook_tree.user,
        )
        slash_page = NotebookPage(
            "slash-page",
            "Summary/Final",
            notebook_tree,
            slash_dir,
            notebook_tree.user,
        )
        slash_dir._children.append(slash_page)  # pyright: ignore[reportPrivateUsage]
        slash_dir._populated = True  # pyright: ignore[reportPrivateUsage]
        notebook_tree._children.append(slash_dir)  # pyright: ignore[reportPrivateUsage]

        assert notebook_tree.traverse(r"/Reports\/2024/Summary\/Final") is slash_page
        assert slash_dir.traverse(r"Summary\/Final") is slash_page

    def test_traverse_parent(self, notebook_tree: Notebook):
        """Test traversing with '..'."""
        folder_a = notebook_tree[Index.Id : "dir-1"]
        parent = folder_a.traverse("..")
        assert parent is notebook_tree

    def test_traverse_not_found(self, notebook_tree: Notebook):
        """Test traversing to a non-existent path."""
        with pytest.raises(
            TraversalError,
            match='Unable to traverse "/NonExistent" at segment "NonExistent"',
        ) as err:
            notebook_tree.traverse("NonExistent")
        assert err.value.path == "/NonExistent"
        assert err.value.segment == "NonExistent"
        assert err.value.parent == "/"
        assert err.value.available_children == [
            "Test Folder A",
            "Test Folder B",
            "Test Page 1",
        ]

    def test_traverse_not_a_directory(self, notebook_tree: Notebook):
        """Test traversing through a non-directory node."""
        with pytest.raises(
            TraversalError,
            match='Unable to traverse "/Test Page 1/Something" at segment "Something"',
        ) as err:
            notebook_tree.traverse("Test Page 1/Something")
        assert err.value.path == "/Test Page 1/Something"
        assert err.value.segment == "Something"
        assert err.value.available_children is None

    def test_getitem_invalid_key_type_raises(self, notebook_tree: Notebook):
        """Test __getitem__ raises TypeError for unsupported key types."""
        with pytest.raises(TypeError, match="Invalid key type"):
            notebook_tree[cast(Any, 123)]

    def test_is_parent_of(self, notebook_tree: Notebook, notebooks):
        """Test ancestor checks for nodes in the same and different roots."""
        folder_a = notebook_tree[Index.Id : "dir-1"].as_dir()
        page_a = notebook_tree.traverse("/Test Folder A/Dir1 Test Page A")
        other_notebook = notebooks[Index.Id : "testnb2"]

        assert notebook_tree.is_parent_of(folder_a)
        assert notebook_tree.is_parent_of(page_a)
        assert folder_a.is_parent_of(page_a)
        assert not folder_a.is_parent_of(folder_a)
        assert not notebook_tree.is_parent_of(other_notebook)

    def test_as_dir_success(self, notebook_tree: Notebook):
        """Test casting a directory node to AbstractTreeContainer."""
        folder_a = notebook_tree[Index.Id : "dir-1"]
        container = folder_a.as_dir()
        assert isinstance(container, AbstractTreeContainer)

    def test_as_dir_failure(self, notebook_tree: Notebook):
        """Test casting a non-directory node to AbstractTreeContainer."""
        page_1 = notebook_tree[Index.Id : "page-1"]
        with pytest.raises(TypeError, match="Node is not a directory"):
            page_1.as_dir()

    def test_as_page_success(self, notebook_tree: Notebook):
        """Test casting a page node to NotebookPage."""
        page_1 = notebook_tree[Index.Id : "page-1"]
        page = page_1.as_page()
        assert isinstance(page, NotebookPage)

    def test_as_page_failure(self, notebook_tree: Notebook):
        """Test casting a directory node to NotebookPage."""
        folder_a = notebook_tree[Index.Id : "dir-1"]
        with pytest.raises(TypeError, match="Node is not a page"):
            folder_a.as_page()

    def test_name_setter(self, client, notebook_tree: Notebook):
        """Test updating a node's name."""
        page = expect_page(notebook_tree[Index.Id : "page-1"])
        client.api_response = client.xml("success")

        page.name = "New Name"

        assert page.name == "New Name"
        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/update_node"
        assert api_call[1]["display_text"] == "New Name"

    def test_directory_rename_invalidates_descendant_path_cache(
        self, client, notebook_tree: Notebook
    ):
        """Test renaming a directory clears cached descendant paths."""
        folder_a = expect_dir(notebook_tree[Index.Id : "dir-1"])
        page_a = expect_page(notebook_tree.traverse("/Test Folder A/Dir1 Test Page A"))
        original_path = str(page_a.path)
        assert original_path == "/Test Folder A/Dir1 Test Page A"

        client.api_response = client.xml("success")
        folder_a.name = "Renamed Folder A"

        assert str(page_a.path) == "/Renamed Folder A/Dir1 Test Page A"
        assert page_a.traverse("..") is folder_a

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/update_node"
        assert api_call[1]["display_text"] == "Renamed Folder A"

    def test_move_to(self, client, notebook_tree: Notebook):
        """Test moving a node to a new container."""
        page = expect_page(notebook_tree[Index.Id : "page-1"])
        folder_a = expect_dir(notebook_tree[Index.Id : "dir-1"])
        old_parent = page.parent

        client.api_response = client.xml("success")

        page.move_to(folder_a)

        assert page.parent is folder_a
        assert page in folder_a.children
        assert page not in old_parent.children

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/update_node"
        assert api_call[1]["parent_tree_id"] == folder_a.tree_id

    def test_move_to_invalidates_descendant_path_cache(
        self, client, notebook_tree: Notebook
    ):
        """Test moving a directory clears cached descendant paths."""
        destination = expect_dir(notebook_tree[Index.Id : "dir-1"])
        source_dir = expect_dir(notebook_tree[Index.Id : "dir-2"])
        descendant = expect_dir(
            notebook_tree.traverse(
                "/Test Folder B/Dir2 Subfolder B/Dir2 Subfolder B Subfolder"
            )
        )
        original_path = str(descendant.path)
        assert (
            original_path
            == "/Test Folder B/Dir2 Subfolder B/Dir2 Subfolder B Subfolder"
        )

        client.api_response = client.xml("success")
        source_dir.move_to(destination)

        assert (
            str(descendant.path)
            == "/Test Folder A/Test Folder B/Dir2 Subfolder B/Dir2 Subfolder B Subfolder"
        )
        assert descendant.traverse("..").name == "Dir2 Subfolder B"

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/update_node"
        assert api_call[1]["parent_tree_id"] == destination.tree_id

    def test_move_to_self_raises_without_api_call(
        self, client, notebook_tree: Notebook
    ):
        """Test move_to rejects moving a directory into itself locally."""
        folder_a = expect_dir(notebook_tree[Index.Id : "dir-1"])

        with pytest.raises(ValueError, match="Cannot move a node to itself"):
            folder_a.move_to(folder_a)

        assert client.api_calls == ()

    def test_move_to_descendant_raises_without_api_call(
        self, client, notebook_tree: Notebook
    ):
        """Test move_to rejects moving a directory into a descendant locally."""
        source_dir = expect_dir(notebook_tree[Index.Id : "dir-2"])
        descendant_dir = expect_dir(source_dir[Index.Id : "dir-2-1"])

        with pytest.raises(
            ValueError, match="Cannot move a directory into one of its descendants"
        ):
            source_dir.move_to(descendant_dir)

        assert client.api_calls == ()

    def test_move_to_other_notebook_raises_without_api_call(
        self, client, notebook_tree: Notebook, notebooks
    ):
        """Test move_to rejects cross-notebook moves locally."""
        page = expect_page(notebook_tree[Index.Id : "page-1"])
        other_notebook = notebooks[Index.Id : "testnb2"]

        with pytest.raises(ValueError, match="Cannot move a node across notebooks"):
            page.move_to(other_notebook)

        assert client.api_calls == ()

    def test_delete(self, client, notebook_tree: Notebook):
        """Test deleting a node (moving to API Deleted Items)."""
        page = notebook_tree[Index.Id : "page-1"].as_page()
        # 2. Create "API Deleted Items" directory
        client.api_response = client.tree_node_response("deleted-dir")
        # 3. Update name
        client.api_response = client.xml("success")
        # 4. Move to deleted directory
        client.api_response = client.xml("success")

        page.delete()

        assert "Deleted at" in page.name
        assert page.parent.name == "API Deleted Items"

        # Verify sequence of calls
        _ = client.pop_api_call()  # insert_node for dir creation
        _ = client.pop_api_call()  # update_node for name
        _ = client.pop_api_call()  # update_node for move

    def test_delete_api_deleted_items_rejected_before_rename(
        self, client, notebook_tree: Notebook
    ):
        """Deleting the 'API Deleted Items' directory is rejected before any mutation."""
        client.api_response = client.tree_node_response("deleted-dir")
        trash = notebook_tree.dir("API Deleted Items")
        client.clear_api_calls()
        original_name = trash.name

        with pytest.raises(ValueError, match="web interface"):
            trash.delete()

        assert trash.name == original_name
        assert client.api_calls == ()

    def test_contains(self, notebook_tree: Notebook):
        """Test __contains__ handles strings and indexed slices properly."""
        assert "Test Folder A" in notebook_tree
        assert "Missing Folder" not in notebook_tree

        assert slice(Index.Id, "dir-1") in notebook_tree
        assert slice(Index.Id, "missing-id") not in notebook_tree

        assert slice(Index.Name, "Test Folder A") in notebook_tree
        assert slice(Index.Name, "Missing Folder") not in notebook_tree

    def test_mapping_methods(self, notebook_tree: Notebook):
        """Test keys(), values(), and items() on a container."""
        keys = notebook_tree.keys()
        assert "Test Folder A" in keys
        assert "Test Folder B" in keys
        assert "Test Page 1" in keys

        values = notebook_tree.values()
        assert any(v.name == "Test Folder A" for v in values)

        items = notebook_tree.items()
        assert ("Test Folder A", notebook_tree[Index.Id : "dir-1"]) in items

    def test_duplicate_mapping_methods_preserve_duplicate_names(
        self, notebook_tree: Notebook
    ):
        """Test duplicate_* helpers preserve duplicate-name children."""
        duplicate_page = NotebookPage(
            "page-duplicate",
            "Test Page 1",
            notebook_tree,
            notebook_tree,
            notebook_tree.user,
        )
        notebook_tree._children.append(duplicate_page)  # pyright: ignore[reportPrivateUsage]

        keys = notebook_tree.all_keys()
        assert keys.count("Test Page 1") == 2

        values = notebook_tree.all_values()
        duplicate_ids = [node.id for node in values if node.name == "Test Page 1"]
        assert duplicate_ids == ["page-1", "page-duplicate"]

        items = notebook_tree.all_items()
        duplicate_pairs = [
            (name, node.id) for name, node in items if name == "Test Page 1"
        ]
        assert duplicate_pairs == [
            ("Test Page 1", "page-1"),
            ("Test Page 1", "page-duplicate"),
        ]

    def test_children_returns_snapshot(self, client, notebook_tree: Notebook):
        """Test children returns an immutable snapshot instead of a live list."""
        snapshot = notebook_tree.children

        assert isinstance(snapshot, tuple)

        client.api_response = client.tree_node_response("snapshot-page-id")

        notebook_tree.create(NotebookPage, "Snapshot Test Page")

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "Snapshot Test Page"

        assert all(child.name != "Snapshot Test Page" for child in snapshot)
        assert any(
            child.name == "Snapshot Test Page" for child in notebook_tree.children
        )

    def test_children_parse_failure_has_context(self, client, notebook_tree: Notebook):
        """Test malformed tree children raise errors with container and node context."""
        dir_1 = notebook_tree[Index.Id : "dir-1"].as_dir()
        dir_1._populated = False

        client.api_response = client.tree_level_response(
            client.tree_level_node(
                tree_id="broken-child",
                display_text=None,
                is_page=False,
            )
        )

        with pytest.raises(
            TreeChildParseError,
            match=(
                r"Could not parse tree child at /tree-tools/level-nodes/level-node "
                r"for parent tree_id='dir-1': display-text cannot be empty"
            ),
        ):
            _ = dir_1.children

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/get_tree_level"
        assert api_call[1]["parent_tree_id"] == "dir-1"

    def test_enumeration(self, notebook_tree: Notebook):
        """Test enumerate_all, enumerate_dirs, and enumerate_pages."""
        # Max depth 1 by default
        all_items = notebook_tree.enumerate_all()
        assert len(all_items) == 3
        assert "Test Folder A" in all_items
        assert "Test Folder B" in all_items
        assert "Test Page 1" in all_items

        # Deeper enumeration
        all_items_deep = notebook_tree.enumerate_all(depth=2)
        assert "Test Folder A/Dir1 Test Page A" in all_items_deep
        assert "Test Folder A/Dir1 Test Page B" in all_items_deep
        assert "Test Folder B/Dir2 Subfolder A" in all_items_deep

        dirs = notebook_tree.enumerate_dirs(depth=2)
        assert "Test Folder A" in dirs
        assert "Test Folder B/Dir2 Subfolder A" in dirs

        pages = notebook_tree.enumerate_pages(depth=2)
        assert "Test Page 1" in pages
        assert "Test Folder A/Dir1 Test Page A" in pages

        nodes = notebook_tree.enumerate_nodes(depth=2)
        assert any(
            path == "Test Folder A" and node.id == "dir-1" for path, node in nodes
        )
        assert any(
            path == "Test Folder A/Dir1 Test Page A" and node.id == "page-1-1"
            for path, node in nodes
        )

    def test_enumeration_escapes_separator_names_for_traversal(
        self, notebook_tree: Notebook
    ):
        """Test enumerated paths with separator names round-trip through traverse."""
        slash_dir = NotebookDirectory(
            "slash-dir",
            "Reports/2024",
            notebook_tree,
            notebook_tree,
            notebook_tree.user,
        )
        slash_page = NotebookPage(
            "slash-page",
            r"Summary\Final",
            notebook_tree,
            slash_dir,
            notebook_tree.user,
        )
        slash_dir._children.append(slash_page)  # pyright: ignore[reportPrivateUsage]
        slash_dir._populated = True  # pyright: ignore[reportPrivateUsage]
        notebook_tree._children.append(slash_dir)  # pyright: ignore[reportPrivateUsage]

        nodes = notebook_tree.enumerate_nodes(depth=2)

        assert (r"Reports\/2024", slash_dir) in nodes
        assert (r"Reports\/2024/Summary\\Final", slash_page) in nodes
        for path, node in nodes:
            assert notebook_tree.traverse(path) is node

    def test_enumeration_handles_same_name_page_and_directory(
        self, notebook_tree: Notebook
    ):
        """Test directory/page filtering does not misclassify duplicate names."""
        _ = notebook_tree.children

        shared_dir = NotebookDirectory(
            "shared-dir",
            "Shared Name",
            notebook_tree,
            notebook_tree,
            notebook_tree.user,
        )
        shared_page = NotebookPage(
            "shared-page",
            "Shared Name",
            notebook_tree,
            notebook_tree,
            notebook_tree.user,
        )
        notebook_tree._children.extend(  # pyright: ignore[reportPrivateUsage]
            [shared_dir, shared_page]
        )

        dirs = notebook_tree.enumerate_dirs()
        pages = notebook_tree.enumerate_pages()

        assert dirs.count("Shared Name") == 1
        assert pages.count("Shared Name") == 1

    def test_enumeration_warns_on_timeout(self, notebook_tree: Notebook, monkeypatch):
        """Test enumerate_* emits warnings when traversal times out."""
        monotonic_values = iter([0.0, 1.0, 1.1, 1.2])
        monkeypatch.setattr(
            "labapi.tree.mixins.time.monotonic", lambda: next(monotonic_values)
        )

        with pytest.warns(RuntimeWarning, match="partial"):
            all_items = notebook_tree.enumerate_all(timeout=timedelta(seconds=0))
        assert all_items == []

        monotonic_values = iter([0.0, 1.0, 1.1, 1.2])
        monkeypatch.setattr(
            "labapi.tree.mixins.time.monotonic", lambda: next(monotonic_values)
        )
        with pytest.warns(RuntimeWarning, match="partial"):
            dirs = notebook_tree.enumerate_dirs(timeout=timedelta(seconds=0))
        assert dirs == []

        monotonic_values = iter([0.0, 1.0, 1.1, 1.2])
        monkeypatch.setattr(
            "labapi.tree.mixins.time.monotonic", lambda: next(monotonic_values)
        )
        with pytest.warns(RuntimeWarning, match="partial"):
            pages = notebook_tree.enumerate_pages(timeout=timedelta(seconds=0))
        assert pages == []

    def test_enumeration_raise_on_timeout(self, notebook_tree: Notebook):
        """Raise mode is no longer supported in enumeration APIs."""
        with pytest.raises(TypeError):
            notebook_tree.enumerate_all(on_truncation="raise")  # pyright: ignore[reportCallIssue]

    def test_create_page(self, client, notebook_tree: Notebook):
        """Test creating a new page."""
        client.api_response = client.tree_node_response("new-page-id")

        new_page = notebook_tree.create(NotebookPage, "New Page")

        assert isinstance(new_page, NotebookPage)
        assert new_page.name == "New Page"
        assert new_page.id == "new-page-id"
        assert new_page in notebook_tree.children

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "New Page"
        assert api_call[1]["is_folder"] == "false"

    def test_create_directory(self, client, notebook_tree: Notebook):
        """Test creating a new directory."""
        client.api_response = client.tree_node_response("new-dir-id")

        new_dir = notebook_tree.create(NotebookDirectory, "New Folder")

        assert isinstance(new_dir, NotebookDirectory)
        assert new_dir.name == "New Folder"
        assert new_dir.id == "new-dir-id"
        assert new_dir in notebook_tree.children

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "New Folder"
        assert api_call[1]["is_folder"] == "true"

    def test_create_escaped_separator_as_literal_child_name(
        self, client, notebook_tree: Notebook
    ):
        """Test creating a direct child whose name contains a literal slash."""
        client.api_response = client.tree_node_response("slash-page-id")

        new_page = notebook_tree.create(NotebookPage, r"Reports\/2024")

        assert isinstance(new_page, NotebookPage)
        assert new_page.name == "Reports/2024"
        assert new_page.parent is notebook_tree

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "Reports/2024"
        assert api_call[1]["is_folder"] == "false"

    def test_page_creates_parents_with_escaped_separator_segments(
        self, client, notebook_tree: Notebook
    ):
        """Test parent creation preserves literal slashes in path segments."""
        client.api_response = client.tree_node_response("slash-dir-id")
        client.api_response = client.tree_node_response("slash-page-id")

        new_page = notebook_tree.page(r"Reports\/2024/Summary\/Final")

        assert isinstance(new_page, NotebookPage)
        assert new_page.name == "Summary/Final"
        assert new_page.parent.name == "Reports/2024"
        assert new_page.parent.parent is notebook_tree

        dir_call = client.pop_api_call()
        assert dir_call[0] == "tree_tools/insert_node"
        assert dir_call[1]["display_text"] == "Reports/2024"
        assert dir_call[1]["is_folder"] == "true"

        page_call = client.pop_api_call()
        assert page_call[0] == "tree_tools/insert_node"
        assert page_call[1]["display_text"] == "Summary/Final"
        assert page_call[1]["is_folder"] == "false"

    def test_create_page_subclass_uses_page_semantics(
        self, client, notebook_tree: Notebook
    ):
        """Test creating a NotebookPage subclass still uses page semantics."""

        class CustomNotebookPage(NotebookPage):
            pass

        client.api_response = client.tree_node_response("custom-page-id")

        new_page = notebook_tree.create(CustomNotebookPage, "Subclass Page")

        assert isinstance(new_page, CustomNotebookPage)

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "Subclass Page"
        assert api_call[1]["is_folder"] == "false"

    def test_create_directory_subclass_uses_directory_semantics(
        self, client, notebook_tree: Notebook
    ):
        """Test creating a NotebookDirectory subclass still uses directory semantics."""

        class CustomNotebookDirectory(NotebookDirectory):
            pass

        client.api_response = client.tree_node_response("custom-dir-id")

        new_dir = notebook_tree.create(CustomNotebookDirectory, "Subclass Folder")

        assert isinstance(new_dir, CustomNotebookDirectory)

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "Subclass Folder"
        assert api_call[1]["is_folder"] == "true"

    def test_create_nested_with_parents(self, client, notebook_tree: Notebook):
        """Test creating a nested page with parents=True."""
        # 1. Create parent folder "Parent"
        client.api_response = client.tree_node_response("parent-id")
        # 2. Create child page "Child"
        client.api_response = client.tree_node_response("child-id")

        new_page = notebook_tree.create(NotebookPage, "Parent/Child", parents=True)

        assert new_page.name == "Child"
        assert new_page.parent.name == "Parent"
        assert new_page.parent.parent is notebook_tree

        # Verify API calls
        # The recursive create first checks if "Parent" exists
        # In this test, it doesn't, so it calls insert_node for "Parent"
        # then it calls create on the new parent which checks if "Child" exists
        # then it calls insert_node for "Child"

        # We need to be careful with how many calls are made.
        # notebook_tree.create(NotebookPage, "Parent/Child", parents=True)
        #   -> path is ["Parent", "Child"]
        #   -> len(path) != 1
        #   -> self.create(NotebookDirectory, "Parent", parents=True, if_exists=Retain)
        #      -> path is ["Parent"]
        #      -> len(path) == 1
        #      -> self["Parent"] -> returns []
        #      -> insert_node "Parent" -> returns parent-id
        #      -> returns new NotebookDirectory "Parent"
        #   -> next_node.create(NotebookPage, ["Parent", "Child"], parents=True, if_exists=Raise)
        #      -> path is ["Child"] (relative to next_node)
        #      -> len(path) == 1
        #      -> self["Child"] -> returns []
        #      -> insert_node "Child" -> returns child-id
        #      -> returns new NotebookPage "Child"

        api_call1 = client.pop_api_call()
        assert api_call1[0] == "tree_tools/insert_node"
        assert api_call1[1]["display_text"] == "Parent"

        api_call2 = client.pop_api_call()
        assert api_call2[0] == "tree_tools/insert_node"
        assert api_call2[1]["display_text"] == "Child"

    def test_create_empty_path_raises(self, notebook_tree: Notebook):
        """Test create rejects empty paths."""
        with pytest.raises(ValueError, match="Path cannot be empty"):
            notebook_tree.create(NotebookPage, "")

    def test_create_absolute_string_within_container(
        self, client, notebook_tree: Notebook
    ):
        """Test create accepts absolute strings that stay inside the container."""
        folder_a = notebook_tree[Index.Id : "dir-1"].as_dir()
        client.api_response = client.tree_node_response("absolute-page-id")

        new_page = folder_a.create(NotebookPage, "/Test Folder A/Absolute String Page")

        assert isinstance(new_page, NotebookPage)
        assert new_page.name == "Absolute String Page"
        assert new_page.parent is folder_a

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "Absolute String Page"

    def test_create_absolute_string_outside_container_raises_without_api_call(
        self, client, notebook_tree: Notebook
    ):
        """Test create rejects absolute strings that point outside the container."""
        folder_a = notebook_tree[Index.Id : "dir-1"].as_dir()

        with pytest.raises(PathError, match="outside of"):
            folder_a.create(NotebookPage, "/Test Folder B/Outside Page")

        assert client.api_calls == ()

    def test_create_absolute_notebook_path_within_container(
        self, client, notebook_tree: Notebook
    ):
        """Test create still accepts absolute NotebookPath inputs."""
        folder_a = notebook_tree[Index.Id : "dir-1"].as_dir()
        client.api_response = client.tree_node_response("absolute-dir-id")

        new_dir = folder_a.create(
            NotebookDirectory,
            NotebookPath(EscapedSegment("/Test Folder A/Absolute String Dir")),
        )

        assert isinstance(new_dir, NotebookDirectory)
        assert new_dir.name == "Absolute String Dir"
        assert new_dir.parent is folder_a

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "Absolute String Dir"

    def test_dir_accepts_absolute_string_within_container(
        self, client, notebook_tree: Notebook
    ):
        """Test dir inherits absolute string handling from create."""
        folder_b = notebook_tree[Index.Id : "dir-2"].as_dir()
        client.api_response = client.tree_node_response("absolute-wrapper-dir-id")

        new_dir = folder_b.dir("/Test Folder B/Absolute Wrapper Dir")

        assert isinstance(new_dir, NotebookDirectory)
        assert new_dir.name == "Absolute Wrapper Dir"
        assert new_dir.parent is folder_b

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "Absolute Wrapper Dir"

    def test_page_accepts_absolute_string_within_container(
        self, client, notebook_tree: Notebook
    ):
        """Test page inherits absolute string handling from create."""
        folder_b = notebook_tree[Index.Id : "dir-2"].as_dir()
        client.api_response = client.tree_node_response("absolute-wrapper-page-id")

        new_page = folder_b.page("/Test Folder B/Absolute Wrapper Page")

        assert isinstance(new_page, NotebookPage)
        assert new_page.name == "Absolute Wrapper Page"
        assert new_page.parent is folder_b

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"
        assert api_call[1]["display_text"] == "Absolute Wrapper Page"

    def test_create_nested_without_parents_raises(self, notebook_tree: Notebook):
        """Test create rejects nested paths when parents=False."""
        with pytest.raises(ValueError, match="parents=True"):
            notebook_tree.create(NotebookPage, "Parent/Child", parents=False)

    def test_create_if_exists_raise(self, notebook_tree: Notebook):
        """Test InsertBehavior.Raise when node exists."""
        with pytest.raises(NodeExistsError, match="already exists"):
            notebook_tree.create(
                NotebookPage, "Test Page 1", if_exists=InsertBehavior.Raise
            )

    def test_create_if_exists_retain(self, notebook_tree: Notebook):
        """Test InsertBehavior.Retain when node exists."""
        existing_page = notebook_tree[Index.Id : "page-1"]
        new_page = notebook_tree.create(
            NotebookPage, "Test Page 1", if_exists=InsertBehavior.Retain
        )

        assert new_page is existing_page
