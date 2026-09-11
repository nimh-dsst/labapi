"""Unit tests for User class."""

from __future__ import annotations

from unittest.mock import Mock

from lxml import etree

from labapi import User
from labapi.tree.collection import Notebooks
from labapi.util.types import NotebookInit


class TestUserUnit:
    """Pure unit tests with all dependencies mocked."""

    def test_user_stores_id(self):
        """Test User stores the provided user ID."""
        mock_client = Mock()
        user = User("test_id_123", "test@example.com", [], mock_client)

        assert user.id == "test_id_123"

    def test_user_stores_client(self):
        """Test User stores the provided client."""
        mock_client = Mock()
        user = User("test_id", "test@example.com", [], mock_client)

        assert user.client is mock_client

    def test_user_api_get_adds_uid(self):
        """Test User.api_get adds uid to the API call."""
        mock_client = Mock()
        mock_element = etree.fromstring(b"<test/>")
        mock_client.api_get.return_value = mock_element

        user = User("user_123", "test@example.com", [], mock_client)
        result = user.api_get("test_endpoint", param1="value1")

        mock_client.api_get.assert_called_once_with(
            "test_endpoint", param1="value1", uid="user_123"
        )
        assert result is mock_element

    def test_user_api_post_adds_uid(self):
        """Test User.api_post adds uid to the API call."""
        mock_client = Mock()
        mock_element = etree.fromstring(b"<test/>")
        mock_client.api_post.return_value = mock_element

        user = User("user_456", "test@example.com", [], mock_client)
        result = user.api_post("test_endpoint", {"data": "test"}, param1="value1")

        mock_client.api_post.assert_called_once_with(
            "test_endpoint", {"data": "test"}, param1="value1", uid="user_456"
        )
        assert result is mock_element


class TestUserIntegration:
    """Integration tests with real objects and mocked API."""

    def test_user_initialization_creates_notebooks(self, client):
        """Test User initialization creates a Notebooks collection."""
        notebooks_init = [
            NotebookInit(id="nb1", name="Notebook 1", is_default=True),
            NotebookInit(id="nb2", name="Notebook 2", is_default=False),
        ]

        user = User("user_id_123", "test@example.com", notebooks_init, client)

        assert user.id == "user_id_123"
        assert isinstance(user.notebooks, Notebooks)
        assert user.client is client
        assert len(user.notebooks) == 2

    def test_user_id_property(self, user: User):
        """Test User.id property returns the user ID."""
        assert user.id == "testid1"

    def test_user_client_property(self, user: User, client):
        """Test User.client property returns the client."""
        assert user.client is client

    def test_user_api_get_full_flow(self, client, user: User):
        """Test User.api_get full flow with MockClient."""
        client.api_response = client.xml(
            "result",
            client.xml("value", "test_value"),
        )

        expected_response = client.api_response
        response = user.api_get("test_endpoint", param1="value1")

        assert response == expected_response

        api_call = client.pop_api_call()
        assert api_call[0] == "test_endpoint"
        assert api_call[1]["param1"] == "value1"
        assert api_call[1]["uid"] == "testid1"

    def test_user_api_post_full_flow(self, client, user: User):
        """Test User.api_post full flow with MockClient."""
        client.api_response = client.xml(
            "result",
            client.xml("success", True),
        )

        user.api_post("test_post_endpoint", {"data": "test_data"}, param1="value1")

        api_call = client.pop_api_call()
        assert api_call[0] == "test_post_endpoint"
        assert api_call[1]["param1"] == "value1"
        assert api_call[1]["uid"] == "testid1"

    def test_user_get_max_upload_size(self, client, user: User):
        """Test User.get_max_upload_size retrieves and parses max file size."""
        client.api_response = client.xml(
            "users",
            client.xml("max-file-size", 104857600, type="integer"),
        )

        max_size = user.get_max_upload_size()

        assert max_size == 104857600

        api_call = client.pop_api_call()
        assert api_call[0] == "users/max_file_size"
        assert api_call[1]["uid"] == "testid1"

    def test_user_get_max_upload_size_clamps_to_api_cap(self, client, user: User):
        """A reported limit above the API cap is clamped to what add_attachment accepts."""
        client.api_response = client.xml(
            "users",
            client.xml("max-file-size", 4_294_967_296, type="integer"),  # 4 GiB
        )

        assert user.get_max_upload_size() == 262_144_000  # 250 MiB API cap

        client.pop_api_call()

    def test_user_notebooks_property(self, user: User):
        """Test User.notebooks property returns Notebooks collection."""
        notebooks = user.notebooks

        assert isinstance(notebooks, Notebooks)
        assert len(notebooks) == 3
