"""Shared test fixtures and mock helpers for the test suite."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import IO, Any, NamedTuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest
import requests

# from dotenv import load_dotenv
from lxml import etree
from typing_extensions import override

import labapi as LA
from labapi.tree.collection import Notebooks

# load_dotenv()


XmlScalar = str | int | float | bool


class RecordedApiCall(NamedTuple):
    """A single API call recorded by ``MockClient`` during a test."""

    api_method_uri: str | Sequence[str]
    params: dict[str, Any]


def pytest_configure(config: pytest.Config):
    """Register custom markers used by the test suite."""
    config.addinivalue_line(
        "markers", "is_interactive: mark test as requiring interactive mode"
    )


def pytest_runtest_setup(item: pytest.Item):
    """Skip interactive tests when pytest output capture is enabled."""
    if "is_interactive" in item.keywords and item.config.getoption("capture") != "no":
        pytest.skip("skipping interactive test in non-interactive mode")


class MockClient(LA.Client):
    """Mock client for testing without hitting the real API."""

    def __init__(self):
        """Initialize the mock client state."""
        super().__init__("https://test-labapi.test", "test", "test")
        self._api_response: list[etree.Element | Exception] = []
        self._api_logs: list[RecordedApiCall] = []

    @override
    def _signature(self, api_method: str, expiry: int) -> str:
        return f"signed:{api_method}:{expiry}"

    @override
    def _sign_url(
        self,
        url: str,
        api_method: str,
        expires_in: timedelta | datetime = timedelta(seconds=60),
    ) -> str:
        scheme, netloc, path, querystring, _f = urlsplit(url)
        query = dict(parse_qsl(querystring))

        if isinstance(expires_in, timedelta):
            expiry = round(
                (datetime.fromtimestamp(0, tz=timezone.utc) + expires_in).timestamp()
                * 1000
            )
        else:
            expiry = round(expires_in.timestamp() * 1000)
        sig = self._signature(api_method, expiry)

        query["akid"] = self._akid
        query["expires"] = str(expiry)
        query["sig"] = sig

        return urlunsplit((scheme, netloc, path, urlencode(query), _f))

    @property
    def api_response(self):
        """Return the next queued API response."""
        return self._api_response[0]

    @api_response.setter
    def api_response(self, value: Exception | etree._Element):
        if isinstance(value, Exception):
            self._api_response.append(value)
            return

        if not isinstance(value, etree._Element):
            raise TypeError(
                "MockClient.api_response expects an Exception or an XML element "
                "built with MockClient.xml()"
            )

        self._api_response.append(deepcopy(value))

    @staticmethod
    def _xml_scalar(value: XmlScalar) -> str:
        """Normalize scalar XML values into API-style text."""
        if isinstance(value, bool):
            return str(value).lower()
        return str(value)

    def xml(
        self,
        tag: str,
        *content: etree._Element | XmlScalar,
        attrs: Mapping[str, XmlScalar] | None = None,
        **attributes: XmlScalar,
    ) -> etree._Element:
        """Build an XML element for a mock API response."""
        if not tag.strip():
            raise ValueError("MockClient.xml requires a non-empty tag name")

        text_nodes = [item for item in content if not isinstance(item, etree._Element)]
        child_nodes = [item for item in content if isinstance(item, etree._Element)]
        if text_nodes and child_nodes:
            raise TypeError(
                "MockClient.xml cannot mix text content with child elements"
            )
        if len(text_nodes) > 1:
            raise TypeError("MockClient.xml accepts at most one text value")

        merged_attributes: dict[str, str] = {}
        if attrs:
            merged_attributes.update(
                {name: self._xml_scalar(value) for name, value in attrs.items()}
            )
        merged_attributes.update(
            {name: self._xml_scalar(value) for name, value in attributes.items()}
        )

        element = etree.Element(tag, attrib=merged_attributes)
        if text_nodes:
            element.text = self._xml_scalar(text_nodes[0])

        for child in child_nodes:
            element.append(deepcopy(child))

        return element

    def bool_xml(self, tag: str, value: bool) -> etree._Element:
        """Build a LabArchives-style boolean element."""
        return self.xml(tag, value, type="boolean")

    def notebook_xml(
        self,
        notebook_id: str,
        name: str,
        *,
        is_default: bool = True,
    ) -> etree._Element:
        """Build a notebook element for mock notebook listings."""
        return self.xml(
            "notebook",
            self.bool_xml("is-default", is_default),
            self.xml("name", name),
            self.xml("id", notebook_id),
        )

    def entry_xml(
        self,
        eid: str,
        *,
        part_type: str | None = None,
        entry_data: str | None = None,
        attach_file_name: str = "",
        attach_content_type: str = "",
    ) -> etree._Element:
        """Build an entry element for mock entry payloads."""
        children: list[etree._Element] = [self.xml("eid", eid)]
        if part_type is not None:
            children.extend(
                [
                    self.xml("part-type", part_type),
                    self.xml("attach-file-name", attach_file_name),
                    self.xml("attach-content-type", attach_content_type),
                ]
            )
        if entry_data is not None:
            children.append(self.xml("entry-data", entry_data))
        return self.xml("entry", *children)

    def entries_response(
        self,
        *entries: etree._Element,
        include_response: bool = True,
    ) -> etree._Element:
        """Build an entries response payload."""
        children: list[etree._Element] = []
        if include_response:
            children.append(self.xml("response"))
        children.extend(entries)
        return self.xml("entries", *children)

    def tree_node_response(self, tree_id: str) -> etree._Element:
        """Build a tree-tools response containing a single node id."""
        return self.xml(
            "tree-tools",
            self.xml("node", self.xml("tree-id", tree_id)),
        )

    def tree_level_node(
        self,
        *,
        tree_id: str,
        display_text: str | None,
        is_page: bool,
        can_read: bool = True,
        can_write: bool = True,
        can_read_comments: bool = True,
        can_write_comments: bool = True,
    ) -> etree._Element:
        """Build a single tree child entry."""
        display_name = (
            self.xml("display-text")
            if display_text is None
            else self.xml("display-text", display_text)
        )
        return self.xml(
            "level-node",
            self.bool_xml("is-page", is_page),
            self.xml("tree-id", tree_id),
            display_name,
            self.xml(
                "user-access",
                self.bool_xml("can-read", can_read),
                self.bool_xml("can-write", can_write),
                self.bool_xml("can-read-comments", can_read_comments),
                self.bool_xml("can-write-comments", can_write_comments),
            ),
        )

    def tree_level_response(self, *level_nodes: etree._Element) -> etree._Element:
        """Build a tree-tools response for get_tree_level calls."""
        return self.xml(
            "tree-tools",
            self.xml("level-nodes", *level_nodes, type="array"),
        )

    @property
    def api_calls(self) -> tuple[RecordedApiCall, ...]:
        """Return a snapshot of all recorded API calls."""
        return tuple(self._api_logs)

    def flush_responses(self):
        """Clear all queued API responses."""
        self._api_response.clear()

    def flush_logs(self):
        """Clear all recorded API logs."""
        self._api_logs.clear()

    def clear_api_calls(self):
        """Clear all recorded API logs."""
        self.flush_logs()

    def clear_log(self):
        """Backward-compatible alias for ``clear_api_calls``."""
        self.clear_api_calls()

    def pop_api_call(self) -> RecordedApiCall:
        """Remove and return the next recorded API call."""
        return self._api_logs.pop(0)

    @override
    def api_get(
        self,
        api_method_uri: str | Sequence[str],
        **kwargs: Any,
    ) -> etree.Element:
        self._api_logs.append(RecordedApiCall(api_method_uri, kwargs))

        assert len(self._api_response) != 0, (
            "Invalid Mock Client State: Did not load API Response"
        )

        api_response = self._api_response.pop(0)

        if isinstance(api_response, Exception):
            raise api_response

        return api_response

    @override
    def raw_api_post(
        self,
        api_method_uri: str | Sequence[str],
        body: Mapping[str, str] | IO[bytes] | IO[str],
        **kwargs: Any,
    ) -> requests.Response:
        log_kwargs = {**kwargs}
        if isinstance(body, Mapping):
            log_kwargs.update(body)

        self._api_logs.append(RecordedApiCall(api_method_uri, log_kwargs))

        assert len(self._api_response) != 0, (
            "Invalid Mock Client State: Did not load API Response"
        )

        api_response = self._api_response.pop(0)

        if isinstance(api_response, Exception):
            raise api_response

        # Create a mock requests.Response object
        mock_response = requests.Response()
        mock_response.status_code = 200
        mock_response._content = etree.tostring(api_response)
        return mock_response


@pytest.fixture
def client():
    """Fixture providing a MockClient instance."""
    client = MockClient()
    yield client
    # Ensure all queued responses were consumed
    assert len(client._api_response) == 0, (
        f"Unused API responses in MockClient: {len(client._api_response)}"
    )
    # Ensure all API calls were verified (logs popped)
    assert len(client.api_calls) == 0, (
        f"Unverified API calls in MockClient: {len(client.api_calls)}"
    )


@pytest.fixture
def user(client: MockClient):
    """Fixture providing a logged-in User instance."""
    client.api_response = client.xml(
        "users",
        client.xml("fullname", "Test User 1"),
        client.xml("id", "testid1"),
        client.bool_xml("auto-login-allowed", False),
        client.xml("request"),
        client.xml(
            "notebooks",
            client.notebook_xml("testnb1", "Test Notebook 1"),
            client.notebook_xml("testnb2", "Test Notebook 3"),
            client.notebook_xml("testnb3", "Test Notebook 3"),
            type="array",
        ),
    )
    result = client.login("test_email@test.test", "test_authcode")
    assert client.pop_api_call() == RecordedApiCall(
        "users/user_access_info",
        {"login_or_email": "test_email@test.test", "password": "test_authcode"},
    )
    client.flush_logs()
    return result


@pytest.fixture
def notebooks(user: LA.User) -> Notebooks:
    """Fixture providing a Notebooks collection."""
    return user.notebooks


@pytest.fixture
def notebook(notebooks: Notebooks):
    """Fixture providing a single Notebook instance."""
    return notebooks[LA.Index.Id : "testnb1"]


@pytest.fixture
def new_notebook(client: MockClient, notebooks: Notebooks):
    """Fixture providing a newly created notebook."""
    client.api_response = client.xml("notebooks", client.xml("nbid", "testnb4"))

    notebook = notebooks.create_notebook("Test Notebook 4")

    client.flush_logs()
    return notebook


def traverse_populate(node: LA.Notebook | LA.NotebookDirectory):
    """Populate a notebook tree recursively."""
    # Trigger population
    len(node)

    for _node in node.values():
        if isinstance(_node, LA.Notebook | LA.NotebookDirectory):
            traverse_populate(_node)


@pytest.fixture
def notebook_tree(client: MockClient, notebook: LA.Notebook) -> LA.Notebook:
    """Fixture providing a fully populated notebook tree structure."""
    notebook.refresh()

    # Level 0
    client.api_response = client.tree_level_response(
        client.tree_level_node(
            tree_id="dir-1",
            display_text="Test Folder A",
            is_page=False,
        ),
        client.tree_level_node(
            tree_id="dir-2",
            display_text="Test Folder B",
            is_page=False,
        ),
        client.tree_level_node(
            tree_id="page-1",
            display_text="Test Page 1",
            is_page=True,
        ),
    )

    # Dir 1
    client.api_response = client.tree_level_response(
        client.tree_level_node(
            tree_id="page-1-1",
            display_text="Dir1 Test Page A",
            is_page=True,
        ),
        client.tree_level_node(
            tree_id="page-1-2",
            display_text="Dir1 Test Page B",
            is_page=True,
        ),
    )

    # Dir 2
    client.api_response = client.tree_level_response(
        client.tree_level_node(
            tree_id="dir-2-1",
            display_text="Dir2 Subfolder A",
            is_page=False,
        ),
        client.tree_level_node(
            tree_id="dir-2-2",
            display_text="Dir2 Subfolder B",
            is_page=False,
        ),
        client.tree_level_node(
            tree_id="page-2-1",
            display_text="Dir2 Test Page",
            is_page=True,
        ),
    )

    # Dir 2 Sub A
    client.api_response = client.tree_level_response()

    # Dir 2 Sub B
    client.api_response = client.tree_level_response(
        client.tree_level_node(
            tree_id="dir-2-2-1",
            display_text="Dir2 Subfolder B Subfolder",
            is_page=False,
        ),
    )

    # Dir 2 Sub B Sub
    client.api_response = client.tree_level_response()

    traverse_populate(notebook)
    client.flush_logs()

    return notebook
