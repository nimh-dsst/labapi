"""Unit tests for NotebookDirectory class."""

from __future__ import annotations

from functools import partial
from unittest.mock import Mock

import pytest

from labapi import Index, Notebook, NotebookDirectory
from labapi.user import User


class TestNotebookDirectoryUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_directory_properties(self):
        """Test NotebookDirectory basic properties."""
        mock_user = Mock(spec=User)
        mock_root = Mock(spec=Notebook)
        mock_parent = Mock(spec=Notebook)

        directory = NotebookDirectory(
            tree_id="dir-1",
            name="Test Folder",
            parent=mock_parent,
            root=mock_root,
            user=mock_user,
        )

        assert directory.id == "dir-1"
        assert directory.name == "Test Folder"
        assert directory.parent is mock_parent
        assert directory.root is mock_root
        assert directory.is_dir() is True

    def test_copy_to_rolls_back_subtree_when_descendant_copy_fails(self):
        """Test NotebookDirectory.copy_to deletes the created subtree on failure."""
        source_dir = Mock(spec=NotebookDirectory)
        source_dir.name = "Source Dir"
        source_dir.is_parent_of.return_value = False

        good_child = Mock()
        failing_child = Mock()
        failing_child.copy_to.side_effect = RuntimeError("descendant copy failed")
        source_dir.children = [good_child, failing_child]

        new_dir = Mock(spec=NotebookDirectory)
        new_dir._discard_partial_copy = partial(
            NotebookDirectory._discard_partial_copy, new_dir
        )

        destination = Mock()
        destination.create.return_value = new_dir

        with pytest.raises(RuntimeError, match="descendant copy failed"):
            NotebookDirectory.copy_to(source_dir, destination, strict=True)

        # Both children were copied into the new directory with strict propagated...
        good_child.copy_to.assert_called_once_with(new_dir, strict=True)
        failing_child.copy_to.assert_called_once_with(new_dir, strict=True)
        # ...and the new directory is rolled back, taking the subtree along.
        new_dir.delete.assert_called_once_with()


class TestNotebookDirectoryIntegration:
    """Integration tests with real objects and mocked API."""

    def test_directory_from_tree(self, notebook_tree: Notebook):
        """Test NotebookDirectory identity and name from the tree fixture."""
        directory = notebook_tree[Index.Id : "dir-1"]

        assert isinstance(directory, NotebookDirectory)
        assert directory.id == "dir-1"
        assert directory.name == "Test Folder A"

    def test_directory_copy_to(self, client, notebook_tree: Notebook):
        """Test NotebookDirectory.copy_to creates a copy with all children."""
        source_dir = notebook_tree[Index.Id : "dir-1"]
        destination = notebook_tree

        assert isinstance(source_dir, NotebookDirectory)
        client.clear_api_calls()

        # 1. Create new directory
        client.api_response = client.tree_node_response("dir-copy")
        # 2. Create copy of child Page A
        client.api_response = client.tree_node_response("page-copy-1")
        # 3. Load entries for Page A (empty)
        client.api_response = client.entries_response()

        # 4. Create copy of child Page B
        client.api_response = client.tree_node_response("page-copy-2")
        # 5. Load entries for Page B (empty)
        client.api_response = client.entries_response()

        new_dir = source_dir.copy_to(destination)

        assert isinstance(new_dir, NotebookDirectory)
        assert new_dir.name == source_dir.name
        assert new_dir.id == "dir-copy"

        api_call = client.pop_api_call()
        assert api_call[0] == "tree_tools/insert_node"

        _ = client.pop_api_call()  # Page A creation
        _ = client.pop_api_call()  # Page A entries
        _ = client.pop_api_call()  # Page B creation
        _ = client.pop_api_call()  # Page B entries
        client.clear_api_calls()

    def test_directory_copy_to_self_raises(self, notebook_tree: Notebook):
        """Test NotebookDirectory.copy_to rejects copying into itself."""
        source_dir = notebook_tree[Index.Id : "dir-1"]
        assert isinstance(source_dir, NotebookDirectory)

        with pytest.raises(ValueError, match="Cannot copy"):
            source_dir.copy_to(source_dir)

    def test_directory_copy_to_descendant_raises(self, notebook_tree: Notebook):
        """Test NotebookDirectory.copy_to rejects copying into a descendant."""
        source_dir = notebook_tree[Index.Id : "dir-2"]
        assert isinstance(source_dir, NotebookDirectory)
        descendant_dir = source_dir[Index.Id : "dir-2-1"]
        assert isinstance(descendant_dir, NotebookDirectory)

        with pytest.raises(ValueError, match="Cannot copy"):
            source_dir.copy_to(descendant_dir)

    def test_copy_to_nested_failure_moves_each_aborted_copy_to_trash(
        self, client, notebook_tree: Notebook
    ):
        """A failure deep in a recursive copy trashes every directory that aborted.

        Exercises the real soft delete: the partial copy leaves the destination
        parent, and each aborted level lands in *API Deleted Items*.
        """
        source_dir = notebook_tree[Index.Id : "dir-2"]
        assert isinstance(source_dir, NotebookDirectory)

        client.api_response = client.tree_node_response("copy-dir-2")
        client.api_response = client.tree_node_response("copy-dir-2-1")
        client.api_response = client.tree_node_response("copy-dir-2-2")
        # Copying the grandchild "Dir2 Subfolder B Subfolder" fails.
        client.api_response = RuntimeError("insert failed")
        # Rollback of "copy-dir-2-2": create API Deleted Items, rename, move.
        client.api_response = client.tree_node_response("trash")
        client.api_response = client.xml("success")
        client.api_response = client.xml("success")
        # Rollback of "copy-dir-2": rename, move.
        client.api_response = client.xml("success")
        client.api_response = client.xml("success")

        with pytest.raises(RuntimeError, match="insert failed"):
            source_dir.copy_to(notebook_tree)

        copy_inserts = [client.pop_api_call() for _ in range(3)]
        assert [call[0] for call in copy_inserts] == ["tree_tools/insert_node"] * 3
        assert [call[1]["parent_tree_id"] for call in copy_inserts] == [
            notebook_tree.tree_id,
            "copy-dir-2",
            "copy-dir-2",
        ]
        failed_insert = client.pop_api_call()
        assert failed_insert[0] == "tree_tools/insert_node"
        assert failed_insert[1]["parent_tree_id"] == "copy-dir-2-2"
        trash_insert = client.pop_api_call()
        assert trash_insert[0] == "tree_tools/insert_node"
        assert trash_insert[1]["display_text"] == "API Deleted Items"
        for rolled_back in ("copy-dir-2-2", "copy-dir-2"):
            rename = client.pop_api_call()
            move = client.pop_api_call()
            assert rename[0] == move[0] == "tree_tools/update_node"
            assert rename[1]["tree_id"] == move[1]["tree_id"] == rolled_back
            assert move[1]["parent_tree_id"] == "trash"
        assert client.api_calls == ()

        trash = notebook_tree[Index.Id : "trash"]
        assert isinstance(trash, NotebookDirectory)
        assert [child.id for child in trash.children] == ["copy-dir-2-2", "copy-dir-2"]
        assert "copy-dir-2" not in [child.id for child in notebook_tree.children]

    def test_copy_to_rollback_failure_warns_and_reraises_original(
        self, client, notebook_tree: Notebook
    ):
        """A failed rollback warns without masking the error that aborted the copy."""
        source_dir = notebook_tree[Index.Id : "dir-1"]
        assert isinstance(source_dir, NotebookDirectory)

        client.api_response = client.tree_node_response("copy-dir-1")
        # Copying the first child page fails...
        client.api_response = RuntimeError("insert failed")
        # ...and so does creating API Deleted Items for the rollback.
        client.api_response = RuntimeError("trash unavailable")

        with (
            pytest.warns(
                RuntimeWarning, match="Failed to roll back.*trash unavailable"
            ),
            pytest.raises(RuntimeError, match="insert failed"),
        ):
            source_dir.copy_to(notebook_tree)

        for _ in range(3):
            assert client.pop_api_call()[0] == "tree_tools/insert_node"
        assert client.api_calls == ()

        # The rollback failed, so the partial copy is still in the destination.
        assert "copy-dir-1" in [child.id for child in notebook_tree.children]
