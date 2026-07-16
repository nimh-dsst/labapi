"""LabArchives User Module.

This module defines the :class:`~labapi.user.User` class, which represents an
authenticated user session with the LabArchives API.
"""

from __future__ import annotations

from typing import IO, TYPE_CHECKING, Any

from labapi.tree.collection import Notebooks
from labapi.util import extract_etree

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from labapi.util import NotebookInit

    from .client import Client


class User:
    """Represents an authenticated LabArchives user session.

    This class holds user-specific information such as the user ID and provides
    an interface to interact with the LabArchives API, particularly for
    accessing and managing notebooks and their contents.
    """

    def __init__(
        self,
        uid: str,
        email: str,
        notebooks: Sequence[NotebookInit],
        client: Client,
    ):
        """Initialize a user session.

        :param uid: The unique ID of the user.
        :param email: The email address of the user.
        :param notebooks: A sequence of :class:`~labapi.util.types.NotebookInit` objects
                          representing the notebooks accessible to the user.
        :param client: The :class:`~labapi.client.Client` instance used for API communication.
        """
        super().__init__()
        self._id: str = uid
        self._email: str = email
        self._notebooks = Notebooks(notebooks, self)
        self._client = client

    @property
    def id(self) -> str:
        """The unique ID of the user."""
        return self._id

    @property
    def email(self) -> str:
        """The email address of the user."""
        return self._email

    @property
    def client(self) -> Client:
        """The :class:`~labapi.client.Client` instance associated with this user session."""
        return self._client

    def api_get(self, api_method_uri: str | Sequence[str], **kwargs: Any):
        """Send a GET request on behalf of this user.

        This method automatically appends the user's ID to the API call.

        :param api_method_uri: The API method URI (e.g., "get_user_settings").
                               Can be a string or a sequence of strings representing path segments.
        :param kwargs: Additional query parameters to pass to the API method.
        :returns: The response from the API, typically an
                  ``lxml.etree.Element``.
        :raises RuntimeError: If the underlying client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.

        Invalid XML propagates ``lxml.etree.XMLSyntaxError``.
        """
        return self._client.api_get(api_method_uri, **kwargs, uid=self._id)

    def api_post(
        self,
        api_method_uri: str | Sequence[str],
        body: Mapping[str, str] | IO[bytes] | IO[str],
        **kwargs: Any,
    ):
        """Send a POST request on behalf of this user.

        This method automatically appends the user's ID to the API call.

        :param api_method_uri: The API method URI (e.g., "create_entry").
                               Can be a string or a sequence of strings representing path segments.
        :param body: The request body, which can be a mapping of form data or a file-like object.
        :param kwargs: Additional query parameters to pass to the API method.
        :returns: The response from the API, typically an
                  ``lxml.etree.Element``.
        :raises RuntimeError: If the underlying client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.

        Invalid XML propagates ``lxml.etree.XMLSyntaxError``.
        """
        return self._client.api_post(api_method_uri, body, **kwargs, uid=self._id)

    def get_max_upload_size(self) -> int:
        """Return the maximum upload size for this user in bytes.

        :returns: The maximum upload size in bytes.
        :raises RuntimeError: If the underlying client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.
        :raises labapi.exceptions.ExtractionError: If the response does not
                                                   include ``max-file-size``.

        Invalid XML propagates ``lxml.etree.XMLSyntaxError``.
        """
        return extract_etree(
            self.api_get("users/max_file_size"), {"max-file-size": int}
        )["max-file-size"]

    @property
    def notebooks(self) -> Notebooks:
        """The user's notebooks.

        :returns: A :class:`~labapi.tree.collection.Notebooks` object managing the user's notebooks.
        """
        return self._notebooks
