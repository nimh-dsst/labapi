"""LabArchives API Client.

This module provides the core client for interacting with the LabArchives API,
handling authentication, request signing, and various API call methods.
"""

from __future__ import annotations

import ssl
import warnings
from base64 import b64encode
from collections.abc import Iterator, Mapping, Sequence
from contextlib import suppress
from datetime import datetime, timedelta
from http.server import SimpleHTTPRequestHandler
from operator import itemgetter
from secrets import token_urlsafe
from socketserver import TCPServer
from time import monotonic
from types import TracebackType
from typing import IO, Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from cryptography.hazmat.primitives.hashes import SHA512
from cryptography.hazmat.primitives.hmac import HMAC
from lxml.etree import Element, fromstring
from requests import Response, Session
from requests import codes as status_codes
from requests.adapters import HTTPAdapter
from typing_extensions import Self, override

from .exceptions import ApiError, AuthenticationError
from .user import User
from .util import NotebookInit, detect_default_browser, extract_etree, getenv, to_bool

# Error codes that indicate an authentication/credential failure.
_AUTH_ERROR_CODES: frozenset[int] = frozenset(
    {
        4506,  # invalid akid
        4514,  # login or password incorrect
        4520,  # invalid signature
        4533,  # session timed out
    }
)

_DEFAULT_AUTH_CALLBACK_HOST = "127.0.0.1"
_DEFAULT_AUTH_CALLBACK_PORT = 8089
_DEFAULT_AUTH_CALLBACK_PATH = "/"
_DEFAULT_AUTH_CALLBACK_TIMEOUT = 300.0


context = ssl.create_default_context()


class StreamingResponse:
    """Wrapper for streamed API responses.

    Exposes both the chunk iterator and the underlying HTTP response object so
    callers can read headers/status without relying on ``StopIteration.value``.
    """

    def __init__(self, response: Response):
        """Initialize a streamed response wrapper."""
        self._response = response
        self._closed = False

    def __getattr__(self, name: str) -> Any:
        """Proxy response attributes (e.g., ``headers`` / ``status_code``)."""
        return getattr(self._response, name)

    def __iter__(self) -> Iterator[bytes]:
        """Iterate over response bytes in 1MiB chunks."""
        try:
            yield from self._response.iter_content(1024 * 1024)
        finally:
            self.close()

    @property
    def response(self) -> Response:
        """The raw response object backing the stream."""
        return self._response

    def close(self) -> None:
        """Close the underlying response and release its connection."""
        if self._closed:
            return
        self._response.close()
        self._closed = True

    def __enter__(self) -> StreamingResponse:
        """Enter a context that guarantees connection cleanup on exit."""
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        """Close the stream when leaving a ``with`` block."""
        self.close()


class _313HTTPAdapter(HTTPAdapter):
    """Custom HTTP adapter that disables strict X.509 certificate verification.

    This adapter is used to work around certain SSL certificate validation issues
    by disabling the VERIFY_X509_STRICT flag. This allows the client to connect
    to servers with certificates that might not pass strict validation.

    .. warning::
       This reduces security by relaxing certificate validation. Use only when
       necessary and with trusted servers.
    """

    def init_poolmanager(self, *args: Any, **kwargs: Any):
        """Initialize the connection pool manager with a custom SSL context.

        This method overrides the default pool manager initialization to inject
        a custom SSL context that disables strict X.509 verification.

        :param args: Positional arguments to pass to the parent init_poolmanager.
        :param kwargs: Keyword arguments to pass to the parent init_poolmanager.
        """
        context = ssl.create_default_context()
        context.verify_flags &= ~ssl.VERIFY_X509_STRICT

        super().init_poolmanager(*args, **kwargs, ssl_context=context)  # pyright: ignore[reportUnknownMemberType]


class _AuthResponseCollector:
    """Context manager for binding and waiting on a loopback auth callback."""

    def __init__(
        self,
        client: Client,
        *,
        port: int = _DEFAULT_AUTH_CALLBACK_PORT,
        callback_path: str = _DEFAULT_AUTH_CALLBACK_PATH,
        timeout: float | None = _DEFAULT_AUTH_CALLBACK_TIMEOUT,
    ):
        """Initialize a loopback auth callback collector."""
        self._client = client
        self._port = port
        self._callback_path = callback_path
        self._timeout = timeout
        self._error: str | None = None
        self._email: str | None = None
        self._auth_code: str | None = None
        self._httpd: TCPServer | None = None

    def __enter__(self) -> Self:
        """Bind the loopback callback server and return this collector."""
        collector = self
        callback_path = self._callback_path

        class AuthRequestHandler(SimpleHTTPRequestHandler):
            def _write_response(self, status_code: int, message: str) -> None:
                self.send_response(status_code)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(message.encode("utf-8"))

            @override
            def do_GET(self) -> None:
                _scheme, _netloc, path, querystring, _fragment = urlsplit(self.path)

                if path != callback_path:
                    self._write_response(404, "Unexpected authentication callback.")
                    return

                query = dict(parse_qsl(querystring))

                error = query.get("error")
                if error is not None:
                    self._write_response(200, f"Error: {error}")
                    collector._error = error
                    return

                auth_code = query.get("auth_code")
                email = query.get("email")
                if auth_code is not None and email is not None:
                    self._write_response(
                        200,
                        "Thanks for Authenticating. Close this Window",
                    )
                    collector._auth_code = auth_code
                    collector._email = email
                    return

                self._write_response(400, "Invalid authentication callback.")

            @override
            def log_message(self, format: str, *args: Any) -> None:
                pass

        class LoopbackTCPServer(TCPServer):
            allow_reuse_address = True

        self._httpd = LoopbackTCPServer(
            (_DEFAULT_AUTH_CALLBACK_HOST, self._port),
            AuthRequestHandler,
        )
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        """Close the loopback callback server."""
        if self._httpd is not None:
            self._httpd.server_close()
            self._httpd = None

    def wait(self) -> User:
        """Wait for a valid callback, then log in and return the user."""
        if self._httpd is None:
            raise RuntimeError(
                "collect_auth_response() must be entered before waiting for a callback"
            )

        deadline = None if self._timeout is None else monotonic() + self._timeout

        while True:
            self._httpd.timeout = deadline if deadline is None else min(deadline, 0.5)
            self._httpd.handle_request()

            if self._error is not None:
                raise AuthenticationError(f"Authentication failed: {self._error}")

            if self._auth_code and self._email:
                return self._client.login(self._email, self._auth_code)

            if deadline is not None:
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise AuthenticationError(
                        "Timed out waiting for the authentication callback"
                    )
                self._httpd.timeout = min(remaining, 0.5)
            else:
                self._httpd.timeout = None


class Client:
    """A client for the LabArchives API.

    This class handles the connection to the LabArchives API
    and provides methods for making authenticated API calls.
    It also manages the authentication flow.
    """

    def __init__(
        self,
        base_url: str | None = None,
        akid: str | None = None,
        akpass: bytes | str | None = None,
        *,
        strict_cert: bool = True,
    ):
        """Initialize a LabArchives API client.

        If any parameter is None, the client will attempt to load values from
        a ``.env`` file using ``python-dotenv``. The environment variables used are:

        - ``API_URL``: The base URL (defaults to ``https://api.labarchives.com``).
        - ``ACCESS_KEYID``: The Access Key ID.
        - ``ACCESS_PWD``: The Access Key Password.

        :param base_url: The base URL of the LabArchives API (e.g., "https://mynotebook.labarchives.com").
                         If None, loaded from the ``API_URL`` environment variable.
        :param akid: The Access Key ID for API authentication.
                     If None, loaded from the ``ACCESS_KEYID`` environment variable.
        :param akpass: The Access Key Password for HMAC-SHA512 signing.
                       If None, loaded from the ``ACCESS_PWD`` environment variable.
        :param strict_cert: Whether to use strict X.509 certificate verification.
                           If False, disables the VERIFY_X509_STRICT flag to allow connections
                           to servers with certificates that may not pass strict validation.
                           Defaults to True. **Warning:** Setting this to False reduces security.
        """
        super().__init__()

        if base_url is None:
            base_url = getenv("API_URL", "https://api.labarchives.com")
        if akid is None:
            akid = getenv("ACCESS_KEYID")
        if akpass is None:
            akpass = getenv("ACCESS_PWD")

        if not akid or not akpass:
            raise AuthenticationError(
                "ACCESS_KEYID or ACCESS_PWD environment variables not set, and parameters were not provided."
            )

        parsed_base_url = urlsplit(base_url)
        normalized_base_url = parsed_base_url.geturl()
        if (
            parsed_base_url.scheme not in {"http", "https"}
            or not parsed_base_url.netloc
        ):
            raise AuthenticationError(
                "Invalid API_URL/base_url: expected a full HTTP(S) URL such as "
                "'https://api.labarchives.com'."
            )

        self._base_url = normalized_base_url
        self._akid = akid
        self._hmac = HMAC(
            bytes(akpass, "utf8") if isinstance(akpass, str) else akpass, SHA512()
        )
        self.session = Session()
        self._closed = False
        if not strict_cert:
            self.session.mount("https://", _313HTTPAdapter())

    def close(self) -> None:
        """Close the underlying requests session.

        Once closed, this client should not be used for further API requests.
        Any :class:`~labapi.user.User` objects derived from this client should
        also be treated as no longer usable for API calls.
        """
        if not self._closed:
            self.session.close()
            self._closed = True

    def __enter__(self) -> Self:
        """Return this client for use as a context manager."""
        return self

    def __exit__(self, *_: object) -> None:
        """Close the client session when leaving a context-manager block."""
        self.close()

    def __del__(self) -> None:
        """Best-effort cleanup for the underlying session at object finalization."""
        with suppress(Exception):
            self.close()

    def _ensure_open(self) -> None:
        """Raise if the client has already been closed."""
        if self._closed:
            raise RuntimeError("Client session is closed")

    def generate_auth_url(self, redirect_url: str) -> str:
        """Generate a LabArchives login URL for the given callback.

        This URL is used to initiate the authorization code flow,
        redirecting the user to LabArchives to grant permissions.

        :param redirect_url: The URL to which LabArchives will redirect the user
                             after successful authentication, containing the authorization code.
        :returns: The full authentication URL.
        """
        return self.construct_url(
            "api_user_login",
            {"redirect_uri": redirect_url},
            expires_in=timedelta(minutes=5),
            should_prefix_api=False,
            signature_method=redirect_url,
        )

    def login(self, user_email: str, auth_code: str) -> User:
        """Log in a user with an authentication code.

        This code can come from the standard browser flow or from a one-hour
        code generated in the LabArchives website.

        This method exchanges the authorization code for user access information,
        including their user ID and available notebooks.

        :param user_email: The email address of the authenticating user.
        :param auth_code: The authorization code received from LabArchives.
        :returns: A :class:`~labapi.user.User` object representing the authenticated user session.
        """
        uid_tree = self.api_get(
            "users/user_access_info", login_or_email=user_email, password=auth_code
        )

        uid = itemgetter("id")(extract_etree(uid_tree, {"id": str}))

        notebooks: list[NotebookInit] = []

        for notebook in uid_tree.iterfind(".//notebook"):
            try:
                notebook_id, notebook_name, is_default = itemgetter(
                    "id", "name", "is-default"
                )(
                    extract_etree(
                        notebook, {"id": str, "name": str, "is-default": to_bool}
                    )
                )
            except ValueError as e:
                warnings.warn(f"Failed to parse notebook entry: {e}", stacklevel=2)
                continue

            notebooks.append(NotebookInit(notebook_id, notebook_name, is_default))

        notebooks.sort(key=lambda k: k.is_default)

        return User(uid, user_email, notebooks, self)

    @staticmethod
    def _handle_request_status(response: Response) -> None:
        """Raise an error for an unsuccessful HTTP response.

        Attempts to parse the LabArchives ``<error>`` XML element from the response
        body to surface a specific error code and description.  Falls back to a
        generic message if the body is not parseable XML.

        :param response: The HTTP response object from the requests library.
        :raises AuthenticationError: For API error codes 4506, 4514, 4520, 4533.
        :raises ApiError: For all other non-200 responses.
        """
        # NOTE: See https://mynotebook.labarchives.com/share/LabArchives%2520API/NDEuNnwyNy8zMi9UcmVlTm9kZS83NDE1Mjk1NTJ8MTA1LjY= [ELN Error Codes]
        if response.status_code != status_codes.ok:
            error_code: int | None = None
            error_desc: str | None = None
            try:
                tree = fromstring(bytes(response.text, encoding="utf-8"))
                code_text = tree.findtext("./error-code")
                if code_text is not None:
                    error_code = int(code_text)
                    error_desc = tree.findtext("./error-description")
            except Exception:
                pass

            if error_code is not None:
                message = f"[{error_code}] {error_desc}"
                if error_code in _AUTH_ERROR_CODES:
                    raise AuthenticationError(message, error_code)
                raise ApiError(message, error_code)

            raise ApiError(
                f"API request failed with status code {response.status_code} "
                f"for URL {response.url}: {response.text}"
            )

    def stream_api_get(
        self, api_method_uri: str | Sequence[str], **kwargs: Any
    ) -> StreamingResponse:
        """Send a GET request and return a streamed response wrapper.

        This is useful for downloading large files or when the response content
        needs to be processed incrementally.

        :param api_method_uri: The API method URI (e.g., "get_file_attachment").
                               Can be a string or a sequence of strings representing path segments.
        :param kwargs: Additional query parameters to pass to the API method.
        :returns: A :class:`StreamingResponse` wrapper with both an iterable
                  byte stream and the full ``requests.Response``.
        :raises RuntimeError: If the client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.
        """
        self._ensure_open()
        request = self.session.get(
            self.construct_url(api_method_uri, query=kwargs), stream=True
        )
        try:
            Client._handle_request_status(request)
        except Exception:
            request.close()
            raise

        return StreamingResponse(request)

    def stream_api_post(
        self,
        api_method_uri: str | Sequence[str],
        body: Mapping[str, str] | IO[bytes] | IO[str],
        **kwargs: Any,
    ) -> StreamingResponse:
        """Send a POST request and return a streamed response wrapper.

        This is useful for uploading large files or when the response content
        needs to be processed incrementally.

        :param api_method_uri: The API method URI (e.g., "upload_file_attachment").
                               Can be a string or a sequence of strings representing path segments.
        :param body: The request body, which can be a mapping of form data or a file-like object.
        :param kwargs: Additional query parameters to pass to the API method.
        :returns: A :class:`StreamingResponse` wrapper with both an iterable
                  byte stream and the full ``requests.Response``.
        :raises RuntimeError: If the client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.
        """
        self._ensure_open()
        request = self.session.post(
            self.construct_url(api_method_uri, query=kwargs), data=body, stream=True
        )
        try:
            Client._handle_request_status(request)
        except Exception:
            request.close()
            raise

        return StreamingResponse(request)

    def raw_api_get(
        self, api_method_uri: str | Sequence[str], **kwargs: Any
    ) -> Response:
        """Send a GET request and return the raw ``requests.Response``.

        This method is suitable for API calls where the full HTTP response,
        including headers and status code, is needed, and the content is not
        expected to be streamed.

        :param api_method_uri: The API method URI (e.g., "get_entry_data").
                               Can be a string or a sequence of strings representing path segments.
        :param kwargs: Additional query parameters to pass to the API method.
        :returns: The ``requests.Response`` object containing the API response.
        :raises RuntimeError: If the client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.
        """
        self._ensure_open()
        request = self.session.get(self.construct_url(api_method_uri, query=kwargs))
        Client._handle_request_status(request)

        return request

    def raw_api_post(
        self,
        api_method_uri: str | Sequence[str],
        body: Mapping[str, str] | IO[bytes] | IO[str],
        **kwargs: Any,
    ) -> Response:
        """Send a POST request and return the raw ``requests.Response``.

        This method is suitable for API calls where the full HTTP response,
        including headers and status code, is needed, and the content is not
        expected to be streamed.

        :param api_method_uri: The API method URI (e.g., "create_entry").
                               Can be a string or a sequence of strings representing path segments.
        :param body: The request body, which can be a mapping of form data or a file-like object.
        :param kwargs: Additional query parameters to pass to the API method.
        :returns: The ``requests.Response`` object containing the API response.
        :raises RuntimeError: If the client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.
        """
        self._ensure_open()
        request = self.session.post(
            self.construct_url(api_method_uri, query=kwargs), data=body
        )
        Client._handle_request_status(request)

        return request

    def api_get(self, api_method_uri: str | Sequence[str], **kwargs: Any) -> Element:
        """Send a GET request and parse the XML response into an element.

        This is the primary method for retrieving structured data from the API.

        :param api_method_uri: The API method URI (e.g., "get_notebook_info").
                               Can be a string or a sequence of strings representing path segments.
        :param kwargs: Additional query parameters to pass to the API method.
        :returns: An ``lxml.etree.Element`` representing the root of the XML
                  response.
        :raises RuntimeError: If the client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.

        Invalid XML propagates ``lxml.etree.XMLSyntaxError``.
        """
        return fromstring(self.raw_api_get(api_method_uri, **kwargs).content)

    def api_post(
        self,
        api_method_uri: str | Sequence[str],
        body: Mapping[str, str] | IO[bytes] | IO[str],
        **kwargs: Any,
    ) -> Element:
        """Send a POST request and parse the XML response into an element.

        This is the primary method for sending data to the API and receiving
        structured XML responses.

        :param api_method_uri: The API method URI (e.g., "create_entry").
                               Can be a string or a sequence of strings representing path segments.
        :param body: The request body, which can be a mapping of form data or a file-like object.
        :param kwargs: Additional query parameters to pass to the API method.
        :returns: An ``lxml.etree.Element`` representing the root of the XML
                  response.
        :raises RuntimeError: If the client session has been closed.
        :raises AuthenticationError: If LabArchives rejects the request due to
                                     invalid or expired credentials.
        :raises ApiError: If LabArchives returns any other non-success response.

        Invalid XML propagates ``lxml.etree.XMLSyntaxError``.
        """
        return fromstring(self.raw_api_post(api_method_uri, body, **kwargs).content)

    def default_authenticate(
        self,
        *,
        port: int = _DEFAULT_AUTH_CALLBACK_PORT,
        timeout: float | None = _DEFAULT_AUTH_CALLBACK_TIMEOUT,
    ) -> User:
        """Authenticate a user with the default browser and a loopback callback.

        This method opens a browser window, directs the user to the LabArchives
        authentication page, and then listens on a loopback callback URL on
        ``127.0.0.1:<port>`` for the redirect containing the authorization code.
        If no compatible browser is available, it falls back to printing the
        authentication URL to the terminal so the user can open it manually.

        .. note::
           Automatic browser launching requires the optional
           ``labapi[builtin-auth]`` dependencies.

        :param port: The local callback port to listen on. Defaults to ``8089``.
        :param timeout: Maximum number of seconds to wait for a valid callback.
                        Defaults to five minutes. Pass ``None`` to wait indefinitely.
        :returns: A :class:`~labapi.user.User` object representing the authenticated user session.
        :raises RuntimeError: If the client session has been closed.
        :raises ImportError: If automatic browser-based authentication is
                             requested but the optional builtin-auth
                             dependencies are not installed.
        :raises AuthenticationError: If authentication fails or times out.
        """
        self._ensure_open()
        callback_path = f"/auth/{token_urlsafe(24)}/"
        auth_url = self.generate_auth_url(
            f"http://{_DEFAULT_AUTH_CALLBACK_HOST}:{port}{callback_path}"
        )

        driver = None
        with self.collect_auth_response(
            port=port,
            callback_path=callback_path,
            timeout=timeout,
        ) as auth_response_collector:
            try:
                try:
                    match detect_default_browser():
                        case "chrome":
                            import selenium.webdriver as webdriver  # pyright: ignore[reportMissingImports]

                            driver = webdriver.Chrome(options=webdriver.ChromeOptions())
                            print("Opening Chrome for authentication...")
                        case "firefox":
                            import selenium.webdriver as webdriver  # pyright: ignore[reportMissingImports]

                            driver = webdriver.Firefox(
                                options=webdriver.FirefoxOptions()
                            )
                            print("Opening Firefox for authentication...")
                        case "edge":
                            import selenium.webdriver as webdriver  # pyright: ignore[reportMissingImports]

                            driver = webdriver.Edge(options=webdriver.EdgeOptions())
                            print("Opening Edge for authentication...")
                        case "terminal":
                            print("Open authentication URL in your browser:")
                            print(auth_url)
                except ImportError as e:
                    raise ImportError(
                        "The builtin-auth dependencies are required for automatic browser-based authentication. "
                        "Install with: pip install labapi[builtin-auth]\n"
                        "Alternatively, use manual authentication with LA_AUTH_BROWSER=terminal."
                    ) from e

                if driver is not None:
                    driver.get(auth_url)
                    print(
                        "Please complete the authentication in the opened browser window..."
                    )

                return auth_response_collector.wait()
            finally:
                if driver is not None:
                    driver.quit()

    def collect_auth_response(
        self,
        *,
        port: int = _DEFAULT_AUTH_CALLBACK_PORT,
        callback_path: str = _DEFAULT_AUTH_CALLBACK_PATH,
        timeout: float | None = _DEFAULT_AUTH_CALLBACK_TIMEOUT,
    ) -> _AuthResponseCollector:
        """Return a context manager for collecting a loopback auth callback.

        The returned collector binds a local HTTP server on enter, waits for a
        valid callback via its ``wait()`` method, and closes the server on
        exit.

        :param port: The local callback port to listen on. Defaults to ``8089``.
        :param callback_path: The callback path to accept. Defaults to ``/``.
        :param timeout: Maximum number of seconds to wait for a valid callback.
                        Defaults to five minutes. Pass ``None`` to wait indefinitely.
        :returns: An enterable collector with a ``wait()`` method for the authentication callback.
        """
        self._ensure_open()
        if not callback_path.startswith("/"):
            callback_path = f"/{callback_path}"

        return _AuthResponseCollector(
            self,
            port=port,
            callback_path=callback_path,
            timeout=timeout,
        )

    def construct_url(
        self,
        api_method_uri: str | Sequence[str],
        query: Mapping[str, Any],
        expires_in: timedelta | datetime | None = None,
        *,
        should_prefix_api: bool = True,
        signature_method: str | None = None,
    ) -> str:
        """Construct a fully qualified and signed URL for an API method.

        This method handles the assembly of the base URL, API method path,
        query parameters, and the HMAC-SHA512 signature required by the LabArchives API.

        :param api_method_uri: The API method URI (e.g., "get_notebook_info").
                               Can be a string or a sequence of strings representing path segments.
        :param query: A dictionary of query parameters to include in the URL.
        :param expires_in: The duration for which the URL should be valid. Can be a
                           `timedelta` object or a specific `datetime` object. If None,
                           defaults to 60 seconds from now.
        :param should_prefix_api: If True, ensures the API method path starts with "api/".
                                  Defaults to True.
        :param signature_method: An optional string to use as the API method for
                                 signature generation, overriding `api_method_uri`.
                                 Useful for methods like `api_user_login` where the
                                 actual method name differs from the URI path.
        :returns: The fully constructed and signed URL.
        :raises ValueError: If ``api_method_uri`` does not contain any non-empty
                            path segments after normalization.
        """
        if isinstance(api_method_uri, str):
            api_method_uri = api_method_uri.split("/")

        raw_method_parts = tuple([part for part in api_method_uri if part.strip()])
        method_parts = (
            raw_method_parts[1:]
            if raw_method_parts and raw_method_parts[0] == "api"
            else raw_method_parts
        )

        if not method_parts:
            raise ValueError(
                "api_method_uri must contain at least one non-empty path segment"
            )

        if should_prefix_api:
            method_parts = ("api", *method_parts)

        api_method = method_parts[-1] if signature_method is None else signature_method

        scheme, netloc, path, _qs, _f = urlsplit(self._base_url)
        path = str(path)

        if not path.endswith("/"):
            path += "/"

        path += "/".join(method_parts)

        url = urlunsplit((scheme, netloc, path, urlencode(query), _f))

        if expires_in:
            return self._sign_url(url, api_method, expires_in)
        return self._sign_url(url, api_method)

    def _signature(self, api_method: str, expiry: int) -> str:
        """Generate the HMAC-SHA512 signature for a LabArchives API request.

        This private method is used internally by `_sign_url` to create the
        cryptographic signature based on the Access Key ID, API method, and expiry.

        :param api_method: The specific API method name used in the signature calculation.
        :param expiry: The expiration timestamp (in milliseconds since epoch) for the request.
        :returns: The base64-encoded HMAC-SHA512 signature.
        """
        hmac = self._hmac.copy()

        hmac.update(f"{self._akid}{api_method}{expiry}".encode())

        sig_raw = hmac.finalize()

        return b64encode(sig_raw).decode()

    def _sign_url(
        self,
        url: str,
        api_method: str,
        expires_in: timedelta | datetime = timedelta(seconds=60),
    ) -> str:
        """Sign a URL and append the LabArchives auth query parameters.

        This private method appends the Access Key ID, expiration timestamp, and
        the generated signature to the URL's query string.

        :param url: The unsigned URL to be signed.
        :param api_method: The specific API method name used for signature generation.
        :param expires_in: The duration for which the URL should be valid. Can be a
                           `timedelta` object or a specific `datetime` object. Defaults
                           to 60 seconds from the current time.
        :returns: The fully signed URL.
        """
        scheme, netloc, path, querystring, _f = urlsplit(url)
        query = dict(parse_qsl(querystring))

        if isinstance(expires_in, timedelta):
            expiry = round((datetime.now() + expires_in).timestamp() * 1000)
        else:
            expiry = round(expires_in.timestamp() * 1000)
        sig = self._signature(api_method, expiry)

        query["akid"] = self._akid
        query["expires"] = str(expiry)
        query["sig"] = sig

        return urlunsplit((scheme, netloc, path, urlencode(query), _f))
