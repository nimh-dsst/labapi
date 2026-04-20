"""Private LabArchives XML and backend mocks used by test fixtures."""

from __future__ import annotations

from base64 import b64encode
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from mimetypes import guess_type
from typing import IO, Any, ClassVar, Self, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from cryptography.hazmat.primitives.hashes import SHA512
from cryptography.hazmat.primitives.hmac import HMAC
from lxml import etree
from requests import Response

import labapi as LA
from labapi.client import StreamingResponse

type XmlScalar = str | int | float | bool
type BackendParams = dict[str, str]
type BackendForm = dict[str, str]
type BackendBodyInput = Mapping[str, str] | IO[bytes] | IO[str]
type BackendBody = BackendForm | bytes

_DEFAULT_TIMESTAMP = "2010-01-23T15:22:04Z"
_DEFAULT_LAST_MODIFIED_BY = "Test User"
_DEFAULT_LAST_MODIFIED_IP = "127.0.0.1"
_AUTH_LATENCY_ALLOWANCE_MS = 120000


class XmlNode(etree.ElementBase):
    """Fluent test XML node that is also a real lxml element."""

    def attr(self, name: str, value: XmlScalar) -> Self:
        self.set(name, str(value).lower() if isinstance(value, bool) else str(value))
        return self

    def children(self, *nodes: etree._Element | XmlScalar) -> Self:
        if not nodes:
            return self

        has_elements = any(isinstance(node, etree._Element) for node in nodes)
        has_scalars = any(not isinstance(node, etree._Element) for node in nodes)

        if has_elements and has_scalars:
            raise TypeError("xml nodes cannot mix text content with child elements")

        if has_elements:
            if etree._Element.text.__get__(self) is not None:
                raise TypeError("xml nodes cannot mix text content with child elements")
            for node in nodes:
                self.append(cast(Any, node))
            return self

        if len(self):
            raise TypeError("xml nodes cannot mix text content with child elements")

        etree._Element.text.__set__(
            self,
            "".join(
                str(node).lower() if isinstance(node, bool) else str(node)
                for node in nodes
            ),
        )
        return self

    def build(self) -> Self:
        return self


_XML_PARSER = etree.XMLParser()
_XML_PARSER.set_element_class_lookup(etree.ElementDefaultClassLookup(element=XmlNode))


class XmlApi:
    """Small fluent XML namespace for tests."""

    def node(self, name: str) -> XmlNode:
        if not name.strip():
            raise ValueError("xml.node() requires a non-empty tag name")
        return cast(XmlNode, _XML_PARSER.makeelement(name))

    def text(self, name: str, value: XmlScalar) -> XmlNode:
        return self.node(name).children(value)

    def boolean(self, name: str, value: bool) -> XmlNode:
        return self.true(name) if value else self.false(name)

    def true(self, name: str) -> XmlNode:
        return self.node(name).attr("type", "boolean").children(True)

    def false(self, name: str) -> XmlNode:
        return self.node(name).attr("type", "boolean").children(False)

    def integer(self, name: str, value: int) -> XmlNode:
        return self.node(name).attr("type", "integer").children(value)

    def datetime(self, name: str, value: str) -> XmlNode:
        return self.node(name).attr("type", "datetime").children(value)

    def array(self, name: str, *children: etree._Element) -> XmlNode:
        return self.node(name).attr("type", "array").children(*children)

    def sig(
        self,
        *,
        expires: int | str,
        class_name: str,
        sig: str,
        method: str,
        akid: str,
    ) -> XmlNode:
        return self.node("request").children(
            self.text("expires", expires),
            self.text("class", class_name),
            self.text("sig", sig),
            self.text("method", method),
            self.text("akid", akid),
        )


@dataclass(slots=True)
class NotebookRecord:
    id: str
    name: str
    is_default: bool = False
    site_notebook_id: str = ""
    signing: str = "SIGNING_NONE"
    add_entry_to_page_top: bool = False
    is_student: bool = False
    child_ids: list[str] = field(default_factory=list)

    def xml(self, xml: XmlApi, *, detailed: bool = False) -> XmlNode:
        if detailed:
            return xml.node("notebook").children(
                xml.text("id", self.id),
                xml.text("name", self.name),
                xml.boolean("add-entry-to-page-top", self.add_entry_to_page_top),
                xml.boolean("is-student", self.is_student),
                xml.text("site-notebook-id", self.site_notebook_id),
                xml.text("signing", self.signing),
            )

        return xml.node("notebook").children(
            xml.boolean("is-default", self.is_default),
            xml.text("name", self.name),
            xml.text("id", self.id),
        )


@dataclass(slots=True)
class TreeNodeRecord:
    tree_id: str
    notebook_id: str
    parent_tree_id: str
    display_text: str
    is_page: bool
    child_ids: list[str] = field(default_factory=list)

    def xml(self, xml: XmlApi, *, tag: str) -> XmlNode:
        user_access = xml.node("user-access").children(
            xml.true("can-read-comments"),
            xml.true("can-write-comments"),
            xml.true("can-write"),
            xml.true("can-read"),
        )
        if tag == "node":
            return xml.node(tag).children(
                user_access,
                xml.text("display-text", self.display_text),
                xml.text("tree-id", self.tree_id),
                xml.boolean("is-page", self.is_page),
            )

        return xml.node(tag).children(
            xml.boolean("is-page", self.is_page),
            xml.text("tree-id", self.tree_id),
            xml.text("display-text", self.display_text),
            user_access,
        )


@dataclass(slots=True)
class EntryRecord:
    eid: str
    notebook_id: str
    page_tree_id: str
    part_type: str
    entry_data: str
    version: int = 1
    created_at: str = _DEFAULT_TIMESTAMP
    updated_at: str = _DEFAULT_TIMESTAMP
    last_modified_verb: str = "entry added via 3rd party app"
    last_modified_by: str = _DEFAULT_LAST_MODIFIED_BY
    last_modified_ip: str = _DEFAULT_LAST_MODIFIED_IP
    caption: str = ""
    attach_file_name: str = ""
    attach_content_type: str = ""
    attach_file_size: int = 0
    change_description: str = ""

    def xml(
        self,
        xml: XmlApi,
        *,
        include_entry_data: bool = False,
        include_comments: bool = False,
        attachment_response: bool = False,
    ) -> XmlNode:
        if attachment_response:
            return xml.node("entry").children(
                xml.text("eid", self.eid),
                xml.text("last-modified-verb", self.last_modified_verb),
                xml.datetime("updated-at", self.updated_at),
                xml.text("attach-file-name", self.attach_file_name),
                xml.integer("attach-file-size", self.attach_file_size),
                xml.node("user-access").children(
                    xml.true("can-read"),
                    xml.true("can-write"),
                ),
                xml.text("caption", self.caption),
                xml.text("part-type", self.part_type),
                xml.integer("version", self.version),
                xml.text("attach-content-type", self.attach_content_type),
                xml.text("last-modified-by", self.last_modified_by),
                xml.datetime("created-at", self.created_at),
            )

        children: list[etree._Element] = [
            xml.text("eid", self.eid),
            xml.datetime("created-at", self.created_at),
            xml.datetime("updated-at", self.updated_at),
            xml.text("last-modified-verb", self.last_modified_verb),
            xml.text("last-modified-by", self.last_modified_by),
            xml.text("last-modified-ip", self.last_modified_ip),
            xml.text("part-type", self.part_type),
            xml.integer("version", self.version),
            xml.text("attach-file-name", self.attach_file_name),
            xml.integer("attach-file-size", self.attach_file_size),
            xml.text("caption", self.caption),
            xml.text("attach-content-type", self.attach_content_type),
            xml.node("user-access").children(
                xml.true("can-read"),
                xml.true("can-write"),
                xml.true("can-read-comments"),
                xml.true("can-write-comments"),
            ),
            xml.text("change-description", self.change_description),
            xml.text(
                "thumb-info",
                "generic" if self.part_type == "Attachment" else "none",
            ),
            xml.text("entry-url", f"https://test-labapi.test/share/{self.eid}"),
        ]
        if include_entry_data:
            children.append(xml.text("entry-data", self.entry_data))
        if include_comments:
            children.append(xml.node("comments"))
        return xml.node("entry").children(*children)


@dataclass(slots=True)
class AttachmentRecord:
    entry_id: str
    filename: str
    mime_type: str
    content: bytes


@dataclass(slots=True)
class BackendReply:
    payload: etree._Element | bytes
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class QueuedClientResponse:
    payload: etree._Element | bytes | Exception
    status_code: int = 200
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class RecordedClientRequest:
    request_type: str
    api_method_uri: str
    params: dict[str, Any]
    body: BackendBody | None = None


class BackendError(Exception):
    def __init__(self, status_code: int, error_code: int, description: str):
        super().__init__(description)
        self.status_code = status_code
        self.error_code = error_code
        self.description = description


class BackendResponse(Response):
    def __init__(
        self,
        *,
        url: str,
        status_code: int,
        content: bytes,
        headers: Mapping[str, str] | None = None,
    ):
        super().__init__()
        self.url = url
        self.status_code = status_code
        self.encoding = "utf-8"
        self._content = content
        if headers:
            self.headers.update(dict(headers))

    def iter_content(
        self,
        chunk_size: int | None = 1,
        decode_unicode: bool = False,
    ):
        payload: bytes | str = self.text if decode_unicode else (self._content or b"")
        if chunk_size is None or chunk_size <= 0:
            chunk_size = max(len(payload), 1)

        for start in range(0, len(payload), chunk_size):
            yield payload[start : start + chunk_size]

    def close(self) -> None:
        return None


class MockBackend:
    _get_routes: ClassVar[dict[str, Callable[..., BackendReply]]] = {}
    _post_routes: ClassVar[dict[str, Callable[..., BackendReply]]] = {}
    _stream_get_routes: ClassVar[dict[str, Callable[..., BackendReply]]] = {}

    def __init__(self):
        self.xml = XmlApi()

        self.access_key_id = "test"
        self.access_key_password = "test"
        self.verify_auth = True

        self.user_id = "testid1"
        self.user_email = "test_email@test.test"
        self.user_password = "test_authcode"
        self.user_full_name = "Test User"
        self.auto_login_allowed = False
        self.max_file_size = 52428800

        self.notebooks: dict[str, NotebookRecord] = {}
        self.directories: dict[str, TreeNodeRecord] = {}
        self.pages: dict[str, TreeNodeRecord] = {}
        self.entries: dict[str, EntryRecord] = {}
        self.attachments: dict[str, AttachmentRecord] = {}

        self._counters = {
            "notebook": 1,
            "directory": 1,
            "page": 1,
            "entry": 1,
        }

    @classmethod
    def get(
        cls, path: str
    ) -> Callable[[Callable[..., BackendReply]], Callable[..., BackendReply]]:
        def register(
            handler: Callable[..., BackendReply],
        ) -> Callable[..., BackendReply]:
            cls._get_routes[path.strip("/")] = handler
            return handler

        return register

    @classmethod
    def post(
        cls, path: str
    ) -> Callable[[Callable[..., BackendReply]], Callable[..., BackendReply]]:
        def register(
            handler: Callable[..., BackendReply],
        ) -> Callable[..., BackendReply]:
            cls._post_routes[path.strip("/")] = handler
            return handler

        return register

    @classmethod
    def stream_get(
        cls, path: str
    ) -> Callable[[Callable[..., BackendReply]], Callable[..., BackendReply]]:
        def register(
            handler: Callable[..., BackendReply],
        ) -> Callable[..., BackendReply]:
            cls._stream_get_routes[path.strip("/")] = handler
            return handler

        return register

    def dispatch_get(self, path: str, params: Mapping[str, str]) -> BackendReply:
        normalized_path = path.strip("/")
        handler = self._get_routes.get(normalized_path)
        if handler is None:
            raise BackendError(404, 404, f"Unsupported mock GET endpoint: {path}")
        if normalized_path == "api_user_login":
            return handler(self, params)
        self._require_auth(normalized_path, params)
        class_name, _, method = normalized_path.partition("/")
        request = self.xml.sig(
            expires=params.get("expires", ""),
            class_name=class_name,
            sig=params.get("sig", ""),
            method=method,
            akid=params.get("akid", ""),
        )
        return handler(self, params, request)

    def dispatch_post(
        self,
        path: str,
        params: Mapping[str, str],
        body: BackendBody,
    ) -> BackendReply:
        normalized_path = path.strip("/")
        self._require_auth(normalized_path, params)
        class_name, _, method = normalized_path.partition("/")
        request = self.xml.sig(
            expires=params.get("expires", ""),
            class_name=class_name,
            sig=params.get("sig", ""),
            method=method,
            akid=params.get("akid", ""),
        )
        handler = self._post_routes.get(normalized_path)
        if handler is None:
            raise BackendError(404, 404, f"Unsupported mock POST endpoint: {path}")
        return handler(self, params, body, request)

    def dispatch_stream_get(
        self,
        path: str,
        params: Mapping[str, str],
    ) -> BackendReply:
        normalized_path = path.strip("/")
        self._require_auth(normalized_path, params)
        handler = self._stream_get_routes.get(normalized_path)
        if handler is None:
            raise BackendError(
                404, 404, f"Unsupported mock streamed GET endpoint: {path}"
            )
        return handler(self, params)

    def _require_auth(
        self,
        path: str,
        params: Mapping[str, str],
        *,
        api_method: str | None = None,
    ) -> None:
        if not self.verify_auth:
            return

        missing = [name for name in ("akid", "expires", "sig") if not params.get(name)]
        if missing:
            raise BackendError(
                401,
                4500,
                "one or more mandatory parameters were not included in your request",
            )

        if params["akid"] != self.access_key_id:
            raise BackendError(401, 4506, "The access key id (akid) is not valid")

        try:
            expires = int(params["expires"])
        except ValueError as exc:
            raise BackendError(401, 4529, "parameter contains invalid value") from exc

        now_ms = round(datetime.now().timestamp() * 1000)
        if now_ms > expires + _AUTH_LATENCY_ALLOWANCE_MS:
            raise BackendError(
                401, 4504, "The expires parameter is no longer valid, it's to old"
            )

        method_name = api_method or path.strip("/").split("/")[-1]
        if params["sig"] != self._signature(method_name, expires):
            raise BackendError(
                401, 4520, "The supplied signature parameter was invalid"
            )

    def _signature(self, api_method: str, expiry: int) -> str:
        hmac = HMAC(self.access_key_password.encode("utf-8"), SHA512())
        hmac.update(f"{self.access_key_id}{api_method}{expiry}".encode())
        return b64encode(hmac.finalize()).decode("utf-8")

    def _next_id(self, kind: str) -> str:
        stores: dict[str, tuple[Mapping[str, object], str]] = {
            "notebook": (self.notebooks, "nb"),
            "directory": (self.directories, "dir"),
            "page": (self.pages, "page"),
            "entry": (self.entries, "eid"),
        }

        store_and_prefix = stores.get(kind)
        if store_and_prefix is None:
            raise ValueError(f"Unknown counter kind: {kind}")

        store, prefix = store_and_prefix

        while True:
            value = self._counters[kind]
            self._counters[kind] += 1
            candidate = f"{prefix}{value}"
            if candidate not in store:
                return candidate

    def _require_keys(self, values: Mapping[str, object], *names: str) -> None:
        missing = [name for name in names if name not in values]
        if missing:
            raise BackendError(
                400,
                4500,
                "one or more mandatory parameters were not included in your request",
            )

    def _require_page(self, notebook_id: str, tree_id: str) -> TreeNodeRecord:
        page = self.pages.get(tree_id)
        if page is None or page.notebook_id != notebook_id:
            raise BackendError(404, 404, f"Page not found: {tree_id}")
        return page

    def _require_entry(self, entry_id: str) -> EntryRecord:
        entry = self.entries.get(entry_id)
        if entry is None:
            raise BackendError(404, 404, f"Entry not found: {entry_id}")
        return entry

    def _require_container(
        self, notebook_id: str, tree_id: str
    ) -> NotebookRecord | TreeNodeRecord:
        if tree_id == "0":
            notebook = self.notebooks.get(notebook_id)
            if notebook is None:
                raise BackendError(404, 404, f"Notebook not found: {notebook_id}")
            return notebook

        directory = self.directories.get(tree_id)
        if directory is None or directory.notebook_id != notebook_id:
            raise BackendError(404, 404, f"Directory not found: {tree_id}")
        return directory


class BackendSession:
    def __init__(self, backend: MockBackend):
        self.backend = backend
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def get(self, url: str, *, stream: bool = False, **_: Any) -> Response:
        path, params = self._parse_url(url)

        try:
            if stream:
                reply = self.backend.dispatch_stream_get(path, params)
                content = (
                    reply.payload
                    if isinstance(reply.payload, bytes)
                    else etree.tostring(reply.payload)
                )
                return BackendResponse(
                    url=url,
                    status_code=reply.status_code,
                    content=content,
                    headers=reply.headers,
                )

            reply = self.backend.dispatch_get(path, params)
            if isinstance(reply.payload, bytes):
                return BackendResponse(
                    url=url,
                    status_code=reply.status_code,
                    content=reply.payload,
                    headers=reply.headers,
                )
            return BackendResponse(
                url=url,
                status_code=reply.status_code,
                content=etree.tostring(reply.payload),
                headers={"Content-Type": "application/xml", **reply.headers},
            )
        except BackendError as exc:
            return self._api_error(url, exc)

    def post(
        self,
        url: str,
        data: BackendBodyInput,
        *,
        stream: bool = False,
        **_: Any,
    ) -> Response:
        del stream

        path, params = self._parse_url(url)
        if isinstance(data, Mapping):
            body: BackendBody = {str(key): str(value) for key, value in data.items()}
        else:
            payload = data.read()
            body = payload.encode("utf-8") if isinstance(payload, str) else payload

        try:
            reply = self.backend.dispatch_post(path, params, body)
            content = (
                reply.payload
                if isinstance(reply.payload, bytes)
                else etree.tostring(reply.payload)
            )
            headers = (
                reply.headers
                if isinstance(reply.payload, bytes)
                else {"Content-Type": "application/xml", **reply.headers}
            )
            return BackendResponse(
                url=url,
                status_code=reply.status_code,
                content=content,
                headers=headers,
            )
        except BackendError as exc:
            return self._api_error(url, exc)

    def _parse_url(self, url: str) -> tuple[str, BackendParams]:
        parsed = urlsplit(url)
        path = parsed.path.strip("/")
        if path.startswith("api/"):
            path = path.removeprefix("api/")
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        return path, params

    def _api_error(self, url: str, error: BackendError) -> Response:
        root = etree.Element("error")
        etree.SubElement(root, "error-code").text = str(error.error_code)
        etree.SubElement(root, "error-description").text = error.description
        return BackendResponse(
            url=url,
            status_code=error.status_code,
            content=etree.tostring(root),
            headers={"Content-Type": "application/xml"},
        )


class MockClient(LA.Client):
    """Queue-driven LabArchives client double for unit-style tests."""

    def __init__(self):
        super().__init__("https://test-labapi.test", "test", "test")
        self.xml = XmlApi()
        self._responses: list[QueuedClientResponse] = []
        self._requests: list[RecordedClientRequest] = []
        self._expected_requests: list[RecordedClientRequest] = []

    def _signature(self, api_method: str, expiry: int) -> str:
        return f"signed:{api_method}:{expiry}"

    def _sign_url(
        self,
        url: str,
        api_method: str,
        expires_in: timedelta | datetime = timedelta(seconds=60),
    ) -> str:
        scheme, netloc, path, querystring, fragment = urlsplit(url)
        query = dict(parse_qsl(querystring))

        if isinstance(expires_in, timedelta):
            expiry = round((datetime.fromtimestamp(0) + expires_in).timestamp() * 1000)
        else:
            expiry = round(expires_in.timestamp() * 1000)

        query["akid"] = self._akid
        query["expires"] = str(expiry)
        query["sig"] = self._signature(api_method, expiry)

        return urlunsplit((scheme, netloc, path, urlencode(query), fragment))

    @property
    def requests(self) -> tuple[RecordedClientRequest, ...]:
        return tuple(self._requests)

    def queue_response(
        self,
        payload: etree._Element | bytes | Exception,
        *,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        if isinstance(payload, etree._Element):
            queued_payload: etree._Element | bytes | Exception = deepcopy(payload)
        elif isinstance(payload, Exception):
            queued_payload = payload
        else:
            queued_payload = payload
        self._responses.append(
            QueuedClientResponse(
                queued_payload,
                status_code=status_code,
                headers=dict(headers or {}),
            )
        )

    def expect_request(
        self,
        *request_type: str,
        body: Mapping[str, str] | bytes | None = None,
        **params: Any,
    ) -> None:
        normalized_request_type = self._normalize_request_type(*request_type)
        self._expected_requests.append(
            RecordedClientRequest(
                request_type=normalized_request_type[0],
                api_method_uri=normalized_request_type[1],
                params=dict(params),
                body=self._normalize_body(body) if body is not None else None,
            )
        )

    def expect_clear(self) -> None:
        problems: list[str] = []
        if self._expected_requests:
            problems.append(
                f"Unverified expected requests in MockClient: {len(self._expected_requests)}"
            )
        if self._responses:
            problems.append(
                f"Unused queued responses in MockClient: {len(self._responses)}"
            )
        self._expected_requests.clear()
        self._responses.clear()
        if problems:
            raise AssertionError("\n".join(problems))

    def raw_api_get(
        self, api_method_uri: str | Sequence[str], **kwargs: Any
    ) -> Response:
        self._ensure_open()
        self._record_request("GET", api_method_uri, kwargs)
        response = self._next_response()
        LA.Client._handle_request_status(response)
        return response

    def raw_api_post(
        self,
        api_method_uri: str | Sequence[str],
        body: Mapping[str, str] | IO[bytes] | IO[str],
        **kwargs: Any,
    ) -> Response:
        self._ensure_open()
        normalized_body = self._normalize_body(body)
        self._record_request("POST", api_method_uri, kwargs, body=normalized_body)
        response = self._next_response()
        LA.Client._handle_request_status(response)
        return response

    def stream_api_get(
        self, api_method_uri: str | Sequence[str], **kwargs: Any
    ) -> StreamingResponse:
        self._ensure_open()
        self._record_request("STREAM_GET", api_method_uri, kwargs)
        response = self._next_response()
        LA.Client._handle_request_status(response)
        return StreamingResponse(response)

    def _record_request(
        self,
        request_type: str,
        api_method_uri: str | Sequence[str],
        params: Mapping[str, Any],
        *,
        body: BackendBody | None = None,
    ) -> None:
        request = RecordedClientRequest(
            request_type=request_type,
            api_method_uri=self._normalize_api_method_uri(api_method_uri),
            params=dict(params),
            body=body,
        )
        self._requests.append(request)

        if not self._expected_requests:
            return

        expected = self._expected_requests.pop(0)
        assert request == expected, (
            "MockClient request mismatch:\n"
            f"expected: {expected!r}\n"
            f"actual:   {request!r}"
        )

    def _next_response(self) -> Response:
        assert self._responses, "Invalid MockClient state: no queued response loaded"
        queued = self._responses.pop(0)

        if isinstance(queued.payload, Exception):
            raise queued.payload

        content = (
            etree.tostring(queued.payload)
            if isinstance(queued.payload, etree._Element)
            else queued.payload
        )
        headers = (
            {"Content-Type": "application/xml", **queued.headers}
            if isinstance(queued.payload, etree._Element)
            else dict(queued.headers)
        )
        return BackendResponse(
            url="https://test-labapi.test/mock",
            status_code=queued.status_code,
            content=content,
            headers=headers,
        )

    @staticmethod
    def _normalize_api_method_uri(api_method_uri: str | Sequence[str]) -> str:
        if isinstance(api_method_uri, str):
            return api_method_uri
        return "/".join(api_method_uri)

    @classmethod
    def _normalize_request_type(cls, *request_type: str) -> tuple[str, str]:
        if len(request_type) < 2:
            raise TypeError(
                "MockClient.expect_request() requires a request type and API method URI"
            )
        return request_type[0], cls._normalize_api_method_uri(request_type[1:])

    @staticmethod
    def _normalize_body(
        body: Mapping[str, str] | IO[bytes] | IO[str] | bytes | None,
    ) -> BackendBody:
        if body is None:
            raise TypeError("MockClient request bodies cannot be None")
        if isinstance(body, bytes):
            return body
        if isinstance(body, Mapping):
            return {str(key): str(value) for key, value in body.items()}
        payload = body.read()
        return payload.encode("utf-8") if isinstance(payload, str) else payload


@MockBackend.get("api_user_login")
def backend_api_user_login(
    self: MockBackend, params: Mapping[str, str]
) -> BackendReply:
    redirect_uri = params.get("redirect_uri")
    if not redirect_uri:
        raise BackendError(
            401,
            4500,
            "one or more mandatory parameters were not included in your request",
        )

    try:
        self._require_auth("api_user_login", params, api_method=redirect_uri)
    except BackendError as error:
        separator = "&" if "?" in redirect_uri else "?"
        return BackendReply(
            b"",
            status_code=302,
            headers={
                "Location": (
                    f"{redirect_uri}{separator}"
                    f"{urlencode({'error': error.description})}"
                )
            },
        )

    separator = "&" if "?" in redirect_uri else "?"
    location = (
        f"{redirect_uri}{separator}"
        f"{urlencode({'auth_code': self.user_password, 'email': self.user_email})}"
    )

    return BackendReply(
        b"",
        status_code=302,
        headers={"Location": location},
    )


@MockBackend.get("users/user_access_info")
def backend_user_access_info(
    self: MockBackend, params: Mapping[str, str], request: XmlNode
) -> BackendReply:
    self._require_keys(params, "login_or_email", "password")
    if (
        params["login_or_email"] != self.user_email
        or params["password"] != self.user_password
    ):
        raise BackendError(401, 4514, "Login/password information is incorrect")

    xml = self.xml
    return BackendReply(
        xml.node("users").children(
            xml.text("fullname", self.user_full_name),
            xml.text("id", self.user_id),
            xml.boolean("auto-login-allowed", self.auto_login_allowed),
            request.children(
                xml.text("login-or-email", params.get("login_or_email", "")),
            ),
            xml.array(
                "notebooks",
                *[notebook.xml(xml) for notebook in self.notebooks.values()],
            ),
        )
    )


@MockBackend.get("users/max_file_size")
def backend_max_file_size(
    self: MockBackend, params: Mapping[str, str], request: XmlNode
) -> BackendReply:
    self._require_keys(params, "uid")
    xml = self.xml
    return BackendReply(
        xml.node("users").children(
            request.children(xml.text("uid", params.get("uid", ""))),
            xml.integer("max-file-size", self.max_file_size),
        )
    )


@MockBackend.get("notebooks/create_notebook")
def backend_create_notebook(
    self: MockBackend, params: Mapping[str, str], request: XmlNode
) -> BackendReply:
    self._require_keys(params, "uid", "name", "initial_folders")
    notebook = NotebookRecord(
        id=self._next_id("notebook"),
        name=params["name"],
        is_default=False,
        site_notebook_id=params.get("site_notebook_id", ""),
    )
    self.notebooks[notebook.id] = notebook

    xml = self.xml
    return BackendReply(
        xml.node("notebooks").children(
            xml.text("nbid", notebook.id),
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("name", params.get("name", "")),
                xml.text("site-notebook-id", params.get("site_notebook_id", "")),
                xml.text("initial-folders", params.get("initial_folders", "")),
            ),
        )
    )


@MockBackend.get("notebooks/modify_notebook_info")
def backend_modify_notebook_info(
    self: MockBackend, params: Mapping[str, str], request: XmlNode
) -> BackendReply:
    self._require_keys(params, "uid", "nbid")
    if not any(
        name in params
        for name in ("name", "site_notebook_id", "signing", "add_entry_position")
    ):
        raise BackendError(
            400,
            4500,
            "one or more mandatory parameters were not included in your request",
        )

    notebook = self.notebooks.get(params["nbid"])
    if notebook is None:
        raise BackendError(404, 404, f"Notebook not found: {params['nbid']}")

    if "name" in params:
        notebook.name = params["name"]
    if "site_notebook_id" in params:
        notebook.site_notebook_id = params["site_notebook_id"]
    if "signing" in params:
        notebook.signing = params["signing"]
    if "add_entry_position" in params:
        notebook.add_entry_to_page_top = params["add_entry_position"].upper() == "TOP"

    xml = self.xml
    return BackendReply(
        xml.node("notebooks").children(
            notebook.xml(xml, detailed=True),
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("nbid", params.get("nbid", "")),
                xml.text("name", params.get("name", "")),
                xml.text("site-notebook-id", params.get("site_notebook_id", "")),
                xml.text("signing", params.get("signing", "")),
                xml.text("add-entry-position", params.get("add_entry_position", "")),
            ),
        )
    )


@MockBackend.get("tree_tools/get_tree_level")
def backend_get_tree_level(
    self: MockBackend, params: Mapping[str, str], request: XmlNode
) -> BackendReply:
    self._require_keys(params, "uid", "nbid", "parent_tree_id")
    notebook_id = params["nbid"]
    parent_tree_id = params["parent_tree_id"]
    container = self._require_container(notebook_id, parent_tree_id)
    children: list[TreeNodeRecord] = []
    for child_id in container.child_ids:
        child = self.directories.get(child_id)
        if child is None or child.notebook_id != notebook_id:
            child = self.pages.get(child_id)
        if child is None or child.notebook_id != notebook_id:
            raise BackendError(404, 404, f"Tree node not found: {child_id}")
        children.append(child)
    xml = self.xml
    return BackendReply(
        xml.node("tree-tools").children(
            xml.array(
                "level-nodes",
                *[child.xml(xml, tag="level-node") for child in children],
            ),
            request.children(
                xml.text("parent-tree-id", parent_tree_id),
                xml.text("uid", params.get("uid", "")),
                xml.text("nbid", notebook_id),
            ),
        )
    )


@MockBackend.get("tree_tools/insert_node")
def backend_insert_node(
    self: MockBackend, params: Mapping[str, str], request: XmlNode
) -> BackendReply:
    self._require_keys(
        params, "uid", "nbid", "parent_tree_id", "display_text", "is_folder"
    )
    notebook_id = params["nbid"]
    parent_tree_id = params["parent_tree_id"]
    parent = self._require_container(notebook_id, parent_tree_id)

    if params["is_folder"] not in {"true", "false"}:
        raise BackendError(400, 4529, "parameter contains invalid value")
    is_folder = params["is_folder"] == "true"
    if is_folder:
        node = TreeNodeRecord(
            tree_id=self._next_id("directory"),
            notebook_id=notebook_id,
            parent_tree_id=parent_tree_id,
            display_text=params["display_text"],
            is_page=False,
        )
        self.directories[node.tree_id] = node
    else:
        node = TreeNodeRecord(
            tree_id=self._next_id("page"),
            notebook_id=notebook_id,
            parent_tree_id=parent_tree_id,
            display_text=params["display_text"],
            is_page=True,
        )
        self.pages[node.tree_id] = node

    parent.child_ids.append(node.tree_id)

    xml = self.xml
    return BackendReply(
        xml.node("tree-tools").children(
            node.xml(xml, tag="node"),
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("nbid", notebook_id),
                xml.text("parent-tree-id", parent_tree_id),
                xml.text("display-text", params.get("display_text", "")),
                xml.text("is-folder", params.get("is_folder", "")),
            ),
        )
    )


@MockBackend.get("tree_tools/update_node")
def backend_update_node(  # noqa: PLR0912
    self: MockBackend, params: Mapping[str, str], request: XmlNode
) -> BackendReply:
    self._require_keys(params, "uid", "nbid", "tree_id")
    if not any(
        name in params for name in ("display_text", "parent_tree_id", "node_position")
    ):
        raise BackendError(
            400,
            4500,
            "one or more mandatory parameters were not included in your request",
        )

    notebook_id = params["nbid"]
    tree_id = params["tree_id"]
    node = self.directories.get(tree_id) or self.pages.get(tree_id)
    if node is None or node.notebook_id != notebook_id:
        raise BackendError(404, 404, f"Tree node not found: {tree_id}")
    current_parent = self._require_container(notebook_id, node.parent_tree_id)
    node.display_text = params.get("display_text", node.display_text)

    requested_parent = params.get("parent_tree_id")
    try:
        requested_position = (
            int(params["node_position"]) if "node_position" in params else None
        )
    except ValueError as exc:
        raise BackendError(400, 4529, "parameter contains invalid value") from exc

    if requested_parent is not None:
        target_parent = self._require_container(notebook_id, requested_parent)
        if node.tree_id in current_parent.child_ids:
            current_parent.child_ids.remove(node.tree_id)
        if (
            target_parent is not current_parent
            and node.tree_id in target_parent.child_ids
        ):
            target_parent.child_ids.remove(node.tree_id)

        if requested_position is None:
            target_parent.child_ids.append(node.tree_id)
        else:
            index = max(0, min(requested_position, len(target_parent.child_ids)))
            target_parent.child_ids.insert(index, node.tree_id)
        node.parent_tree_id = requested_parent
    elif requested_position is not None:
        if node.tree_id in current_parent.child_ids:
            current_parent.child_ids.remove(node.tree_id)
        index = max(0, min(requested_position, len(current_parent.child_ids)))
        current_parent.child_ids.insert(index, node.tree_id)

    xml = self.xml
    return BackendReply(
        xml.node("tree-tools").children(
            node.xml(xml, tag="node"),
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("nbid", notebook_id),
                xml.text("tree-id", params.get("tree_id", "")),
                xml.text("parent-tree-id", params.get("parent_tree_id", "")),
                xml.text("display-text", params.get("display_text", "")),
                xml.text("node-position", params.get("node_position", "")),
            ),
        )
    )


@MockBackend.get("tree_tools/get_entries_for_page")
def backend_get_entries_for_page(
    self: MockBackend, params: Mapping[str, str], request: XmlNode
) -> BackendReply:
    self._require_keys(params, "uid", "nbid", "page_tree_id", "entry_data")
    notebook_id = params["nbid"]
    page = self._require_page(notebook_id, params["page_tree_id"])
    truthy_values = {"1", "true", "yes", "on"}
    if params["entry_data"].strip().lower() not in truthy_values:
        raise BackendError(400, 4529, "parameter contains invalid value")
    include_entry_data = True
    include_comment_data = (
        params.get("comment_data", "").strip().lower() in truthy_values
    )

    entries = [
        entry
        for entry in self.entries.values()
        if entry.notebook_id == notebook_id and entry.page_tree_id == page.tree_id
    ]

    xml = self.xml
    return BackendReply(
        xml.node("entries").children(
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("nbid", notebook_id),
                xml.text("page-tree-id", page.tree_id),
                xml.text("entry-data", params["entry_data"]),
                xml.text("comment-data", params.get("comment_data", "")),
            ),
            *[
                entry.xml(
                    xml,
                    include_entry_data=include_entry_data,
                    include_comments=include_comment_data,
                )
                for entry in entries
            ],
        )
    )


@MockBackend.post("entries/add_entry")
def backend_add_entry(
    self: MockBackend,
    params: Mapping[str, str],
    body: BackendBody,
    request: XmlNode,
) -> BackendReply:
    if not isinstance(body, dict):
        raise BackendError(400, 400, "entries/add_entry expects form data")
    self._require_keys(params, "uid", "nbid", "pid", "part_type")
    self._require_keys(body, "entry_data")

    page = self._require_page(params["nbid"], params["pid"])
    entry = EntryRecord(
        eid=self._next_id("entry"),
        notebook_id=page.notebook_id,
        page_tree_id=page.tree_id,
        part_type=params["part_type"],
        entry_data=body["entry_data"],
        last_modified_verb="entry added via 3rd party app",
        last_modified_by=self.user_full_name,
    )
    self.entries[entry.eid] = entry

    xml = self.xml
    return BackendReply(
        xml.node("entries").children(
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("nbid", params["nbid"]),
                xml.text("pid", params["pid"]),
                xml.text("part-type", params["part_type"]),
                xml.text("entry-data", body["entry_data"]),
            ),
            entry.xml(xml, include_entry_data=True),
        )
    )


@MockBackend.post("entries/update_entry")
def backend_update_entry(
    self: MockBackend,
    params: Mapping[str, str],
    body: BackendBody,
    request: XmlNode,
) -> BackendReply:
    if not isinstance(body, dict):
        raise BackendError(400, 400, "entries/update_entry expects form data")
    self._require_keys(params, "uid", "eid")
    self._require_keys(body, "entry_data")

    entry = self._require_entry(params["eid"])
    entry.entry_data = body["entry_data"]
    entry.version += 1
    entry.updated_at = _DEFAULT_TIMESTAMP
    entry.last_modified_verb = "entry updated via 3rd party app"
    entry.last_modified_by = self.user_full_name

    xml = self.xml
    return BackendReply(
        xml.node("entries").children(
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("eid", params["eid"]),
                xml.text("entry-data", body["entry_data"]),
            ),
            entry.xml(xml, include_entry_data=True),
        )
    )


@MockBackend.post("entries/add_attachment")
def backend_add_attachment(
    self: MockBackend,
    params: Mapping[str, str],
    body: BackendBody,
    request: XmlNode,
) -> BackendReply:
    if not isinstance(body, bytes):
        raise BackendError(400, 400, "entries/add_attachment expects binary data")
    self._require_keys(
        params,
        "uid",
        "filename",
        "caption",
        "nbid",
        "pid",
        "change_description",
    )

    page = self._require_page(params["nbid"], params["pid"])
    filename = params["filename"]
    caption = params.get("caption", filename)
    mime_type = guess_type(filename)[0] or "application/octet-stream"

    entry = EntryRecord(
        eid=self._next_id("entry"),
        notebook_id=page.notebook_id,
        page_tree_id=page.tree_id,
        part_type="Attachment",
        entry_data=caption,
        version=1,
        last_modified_verb="file uploaded via 3rd party app",
        last_modified_by=self.user_full_name,
        last_modified_ip=params.get("client_ip", _DEFAULT_LAST_MODIFIED_IP),
        caption=caption,
        attach_file_name=filename,
        attach_content_type=mime_type,
        attach_file_size=len(body),
        change_description=params.get("change_description", ""),
    )
    self.entries[entry.eid] = entry
    self.attachments[entry.eid] = AttachmentRecord(
        entry_id=entry.eid,
        filename=filename,
        mime_type=mime_type,
        content=body,
    )

    xml = self.xml
    return BackendReply(
        xml.node("entries").children(
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("caption", caption),
                xml.text("filename", filename),
                xml.text("nbid", params["nbid"]),
                xml.text("pid", params["pid"]),
                xml.text("change-description", params["change_description"]),
                xml.text("client-ip", params.get("client_ip", "")),
            ),
            entry.xml(xml, attachment_response=True),
        )
    )


@MockBackend.post("entries/update_attachment")
def backend_update_attachment(
    self: MockBackend,
    params: Mapping[str, str],
    body: BackendBody,
    request: XmlNode,
) -> BackendReply:
    if not isinstance(body, bytes):
        raise BackendError(400, 400, "entries/update_attachment expects binary data")
    self._require_keys(
        params,
        "uid",
        "filename",
        "caption",
        "eid",
        "change_description",
    )

    entry = self._require_entry(params["eid"])
    if entry.part_type != "Attachment":
        raise BackendError(400, 400, f"Entry is not an attachment: {entry.eid}")

    filename = params["filename"]
    caption = params.get("caption", filename)
    mime_type = guess_type(filename)[0] or "application/octet-stream"

    entry.entry_data = caption
    entry.caption = caption
    entry.attach_file_name = filename
    entry.attach_content_type = mime_type
    entry.attach_file_size = len(body)
    entry.version += 1
    entry.updated_at = _DEFAULT_TIMESTAMP
    entry.last_modified_verb = "file uploaded via 3rd party app"
    entry.last_modified_by = self.user_full_name
    entry.last_modified_ip = params.get("client_ip", _DEFAULT_LAST_MODIFIED_IP)
    entry.change_description = params.get("change_description", "")

    self.attachments[entry.eid] = AttachmentRecord(
        entry_id=entry.eid,
        filename=filename,
        mime_type=mime_type,
        content=body,
    )

    xml = self.xml
    return BackendReply(
        xml.node("entries").children(
            request.children(
                xml.text("uid", params.get("uid", "")),
                xml.text("caption", caption),
                xml.text("filename", filename),
                xml.text("eid", params["eid"]),
                xml.text("change-description", params["change_description"]),
                xml.text("client-ip", params.get("client_ip", "")),
            ),
            entry.xml(xml, attachment_response=True),
        )
    )


@MockBackend.stream_get("entries/entry_attachment")
def backend_entry_attachment(
    self: MockBackend, params: Mapping[str, str]
) -> BackendReply:
    self._require_keys(params, "uid", "eid")
    entry = self._require_entry(params["eid"])
    if entry.part_type != "Attachment":
        raise BackendError(400, 400, f"Entry is not an attachment: {entry.eid}")

    attachment = self.attachments.get(entry.eid)
    if attachment is None:
        raise BackendError(404, 404, f"Attachment not found for entry: {entry.eid}")

    return BackendReply(
        attachment.content,
        headers={
            "Content-Type": attachment.mime_type,
            "Content-Disposition": f'attachment; filename="{attachment.filename}"',
        },
    )
