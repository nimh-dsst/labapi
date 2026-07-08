"""Unit tests for Notebooks collection class."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import Mock

import pytest

from labapi import Index, Notebook
from labapi.exceptions import ApiError
from labapi.tree.collection import Notebooks
from labapi.user import User
from labapi.util.types import NotebookInit


class TestNotebooksUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_notebooks_len(self):
        """Test Notebooks.__len__ returns count."""
        mock_user = Mock(spec=User)
        notebooks_init = [
            NotebookInit(id="nb1", name="Notebook 1", is_default=True),
            NotebookInit(id="nb2", name="Notebook 2", is_default=False),
        ]
        notebooks = Notebooks(notebooks_init, mock_user)

        assert len(notebooks) == 2

    def test_notebooks_getitem_by_id_index(self):
        """Test Notebooks.__getitem__ with Index.Id slice."""
        mock_user = Mock(spec=User)
        notebooks_init = [NotebookInit(id="nb1", name="Test", is_default=True)]
        notebooks = Notebooks(notebooks_init, mock_user)

        notebook = notebooks[Index.Id : "nb1"]

        assert isinstance(notebook, Notebook)
        assert notebook.id == "nb1"

    def test_notebooks_getitem_by_name_index(self):
        """Test Notebooks.__getitem__ with Index.Name slice returns list."""
        mock_user = Mock(spec=User)
        notebooks_init = [
            NotebookInit(id="nb1", name="Test", is_default=True),
            NotebookInit(id="nb2", name="Test", is_default=False),
        ]
        notebooks = Notebooks(notebooks_init, mock_user)

        result = notebooks[Index.Name : "Test"]

        assert isinstance(result, list)
        assert len(result) == 2

    def test_notebooks_getitem_by_name_empty(self):
        """Test Notebooks.__getitem__ with Index.Name returns empty list if not found."""
        mock_user = Mock(spec=User)
        notebooks_init = [NotebookInit(id="nb1", name="Test", is_default=True)]
        notebooks = Notebooks(notebooks_init, mock_user)

        result = notebooks[Index.Name : "Nonexistent"]

        assert result == []

    def test_notebooks_getitem_by_string_raises(self):
        """Test Notebooks.__getitem__ with string raises KeyError if not found."""
        mock_user = Mock(spec=User)
        notebooks_init = [NotebookInit(id="nb1", name="Test", is_default=True)]
        notebooks = Notebooks(notebooks_init, mock_user)

        with pytest.raises(
            KeyError, match='Notebook with name "Nonexistent" not found'
        ):
            notebooks["Nonexistent"]

    def test_notebooks_getitem_invalid_key_type_raises(self):
        """Test Notebooks.__getitem__ raises TypeError for unsupported key types."""
        mock_user = Mock(spec=User)
        notebooks_init = [NotebookInit(id="nb1", name="Test", is_default=True)]
        notebooks = Notebooks(notebooks_init, mock_user)

        with pytest.raises(TypeError, match="Invalid key type"):
            notebooks[cast(Any, 123)]

    def test_notebooks_iter(self):
        """Test Notebooks.__iter__ returns iterator over names."""
        mock_user = Mock(spec=User)
        notebooks_init = [
            NotebookInit(id="nb1", name="Notebook 1", is_default=True),
            NotebookInit(id="nb2", name="Notebook 2", is_default=False),
        ]
        notebooks = Notebooks(notebooks_init, mock_user)

        names = list(notebooks)

        assert names == ["Notebook 1", "Notebook 2"]

    def test_notebooks_values(self):
        """Test Notebooks.values returns notebook objects."""
        mock_user = Mock(spec=User)
        notebooks_init = [
            NotebookInit(id="nb1", name="Notebook 1", is_default=True),
            NotebookInit(id="nb2", name="Notebook 2", is_default=False),
        ]
        notebooks = Notebooks(notebooks_init, mock_user)

        values = notebooks.values()

        assert len(values) == 2
        assert all(isinstance(nb, Notebook) for nb in values)

    def test_notebooks_mapping_methods_are_mapping_compatible(self):
        """Test keys(), items(), and values() return mapping views."""
        mock_user = Mock(spec=User)
        notebooks_init = [
            NotebookInit(id="nb1", name="Shared", is_default=True),
            NotebookInit(id="nb2", name="Shared", is_default=False),
            NotebookInit(id="nb3", name="Unique", is_default=False),
        ]
        notebooks = Notebooks(notebooks_init, mock_user)

        keys = notebooks.keys()
        assert set(keys) == {"Shared", "Unique"}

        values = notebooks.values()
        assert [notebook.id for notebook in values] == ["nb1", "nb3"]

        items = notebooks.items()
        assert [(name, notebook.id) for name, notebook in items] == [
            ("Shared", "nb1"),
            ("Unique", "nb3"),
        ]

    def test_notebooks_mapping_views_preserve_first_match_for_duplicates(self):
        """Test that keys/items/values agree with getitem for duplicate names (#214).

        keys(), items(), and values() must retain the *first* notebook when
        there are duplicate names, matching the behaviour of __getitem__.
        """
        mock_user = Mock(spec=User)
        notebooks_init = [
            NotebookInit(id="nb1", name="dup", is_default=True),
            NotebookInit(id="nb2", name="dup", is_default=False),
        ]
        notebooks = Notebooks(notebooks_init, mock_user)

        # __getitem__ already returns the first match
        assert notebooks["dup"].id == "nb1"

        # mapping views must agree with __getitem__
        keys = list(notebooks.keys())
        assert keys == ["dup"]

        values_ids = [nb.id for nb in notebooks.values()]
        assert values_ids == ["nb1"]

        items_ids = [(name, nb.id) for name, nb in notebooks.items()]
        assert items_ids == [("dup", "nb1")]

    def test_notebooks_duplicate_mapping_methods_preserve_duplicate_names(self):
        """Test duplicate_* methods preserve duplicate notebook names."""
        mock_user = Mock(spec=User)
        notebooks_init = [
            NotebookInit(id="nb1", name="Shared", is_default=True),
            NotebookInit(id="nb2", name="Shared", is_default=False),
            NotebookInit(id="nb3", name="Unique", is_default=False),
        ]
        notebooks = Notebooks(notebooks_init, mock_user)

        keys = notebooks.all_keys()
        assert keys == ["Shared", "Shared", "Unique"]

        values = notebooks.all_values()
        assert [notebook.id for notebook in values] == ["nb1", "nb2", "nb3"]

        items = notebooks.all_items()
        assert [(name, notebook.id) for name, notebook in items] == [
            ("Shared", "nb1"),
            ("Shared", "nb2"),
            ("Unique", "nb3"),
        ]


class TestNotebooksIntegration:
    """Integration tests with real objects and mocked API."""

    def test_notebooks_getitem_by_string(self, notebooks: Notebooks):
        """Test Notebooks.__getitem__ with string name."""
        notebook = notebooks["Test Notebook 1"]

        assert isinstance(notebook, Notebook)
        assert notebook.name == "Test Notebook 1"
        assert notebook.id == "testnb1"

    def test_notebooks_getitem_by_id(self, notebooks: Notebooks):
        """Test Notebooks.__getitem__ with Index.Id slice."""
        notebook = notebooks[Index.Id : "testnb2"]

        assert isinstance(notebook, Notebook)
        assert notebook.id == "testnb2"

    def test_notebooks_getitem_by_name(self, notebooks: Notebooks):
        """Test Notebooks.__getitem__ with Index.Name slice."""
        notebooks_list = notebooks[Index.Name : "Test Notebook 3"]

        assert isinstance(notebooks_list, list)
        assert len(notebooks_list) == 2
        assert notebooks_list[0].id == "testnb2"
        assert notebooks_list[1].id == "testnb3"

    def test_notebooks_create_notebook(self, client, notebooks: Notebooks):
        """Test Notebooks.create_notebook creates a new notebook."""
        client.api_response = client.xml(
            "notebooks",
            client.xml("nbid", "new_nb_id"),
        )

        new_notebook = notebooks.create_notebook("New Notebook")

        assert isinstance(new_notebook, Notebook)
        assert new_notebook.id == "new_nb_id"
        assert new_notebook.name == "New Notebook"
        assert new_notebook.is_default is False

        assert len(notebooks) == 4
        assert notebooks[Index.Id : "new_nb_id"] is new_notebook

        api_call = client.pop_api_call()
        assert api_call[0] == "notebooks/create_notebook"
        assert api_call[1]["name"] == "New Notebook"
        assert api_call[1]["initial_folders"] == "Empty"

    def test_notebooks_name_index_snapshot_stable_after_mutation(
        self, client, notebooks: Notebooks
    ):
        """Previously returned name-index snapshots should not change after create."""
        snapshot = notebooks[Index.Name : "Test Notebook 3"]

        client.api_response = client.xml(
            "notebooks",
            client.xml("nbid", "new_nb_id_for_snapshot_test"),
        )
        notebooks.create_notebook("Test Notebook 3")
        client.clear_api_calls()

        assert len(snapshot) == 2
        assert all(nb.id in {"testnb2", "testnb3"} for nb in snapshot)

        latest = notebooks[Index.Name : "Test Notebook 3"]
        assert len(latest) == 3

    def test_notebooks_create_notebook_duplicate_id_raises(
        self, client, notebooks: Notebooks
    ):
        """Test Notebooks.create_notebook raises RuntimeError if API returns existing ID."""
        client.api_response = client.xml(
            "notebooks",
            client.xml("nbid", "testnb1"),
        )

        with pytest.raises(ApiError, match="API returned an existing notebook ID"):
            notebooks.create_notebook("Duplicate")
        client.clear_api_calls()
