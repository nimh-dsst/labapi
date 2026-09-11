"""Unit tests for NotebookDirectory class."""

from __future__ import annotations

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
        new_dir.id = "new-dir-id"

        destination = Mock()
        destination.create.return_value = new_dir

        with pytest.raises(RuntimeError, match="descendant copy failed"):
            NotebookDirectory.copy_to(source_dir, destination)

        # Both children were copied into the newly created directory before the abort...
        good_child.copy_to.assert_called_once_with(new_dir)
        failing_child.copy_to.assert_called_once_with(new_dir)
        # ...and deleting that directory cascades, rolling back the whole partial subtree.
        new_dir.delete.assert_called_once_with()

    def test_copy_to_warns_when_subtree_rollback_fails(self):
        """Test NotebookDirectory.copy_to warns (but still re-raises) if rollback fails."""
        source_dir = Mock(spec=NotebookDirectory)
        source_dir.name = "Source Dir"
        source_dir.is_parent_of.return_value = False

        failing_child = Mock()
        failing_child.copy_to.side_effect = RuntimeError("descendant copy failed")
        source_dir.children = [failing_child]

        new_dir = Mock(spec=NotebookDirectory)
        new_dir.id = "new-dir-id"
        new_dir.delete.side_effect = RuntimeError("delete failed")

        destination = Mock()
        destination.create.return_value = new_dir

        with (
            pytest.warns(RuntimeWarning, match="Failed to roll back"),
            pytest.raises(RuntimeError, match="descendant copy failed"),
        ):
            NotebookDirectory.copy_to(source_dir, destination)

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
