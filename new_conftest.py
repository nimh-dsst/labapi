"""Thin fixture facade for the LabArchives mock test support."""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, cast

import pytest

import labapi as LA

_MOCKS_MODULE_NAME = "_labapi_mocks_impl"
_MOCKS_PATH = Path(__file__).with_name("tests") / "_labapi_mocks.py"
_MOCKS_SPEC = spec_from_file_location(_MOCKS_MODULE_NAME, _MOCKS_PATH)
if _MOCKS_SPEC is None or _MOCKS_SPEC.loader is None:
    raise ImportError(f"Could not load LabArchives mocks from {_MOCKS_PATH}")

_MOCKS_MODULE = module_from_spec(_MOCKS_SPEC)
sys.modules.setdefault(_MOCKS_MODULE_NAME, _MOCKS_MODULE)
_MOCKS_SPEC.loader.exec_module(_MOCKS_MODULE)

BackendSession = cast(type[Any], _MOCKS_MODULE.BackendSession)
MockClient = cast(type[Any], _MOCKS_MODULE.MockClient)
MockBackend = cast(type[Any], _MOCKS_MODULE.MockBackend)
RecordedClientRequest = cast(type[Any], _MOCKS_MODULE.RecordedClientRequest)
XmlApi = cast(type[Any], _MOCKS_MODULE.XmlApi)


@pytest.fixture
def xml() -> Any:
    """Return the shared fluent XML helper for tests."""
    return XmlApi()


@pytest.fixture
def backend() -> Any:
    """Return a fresh stateful mock LabArchives backend."""
    return MockBackend()


@pytest.fixture
def client() -> Any:
    """Return a queue-driven mock LabArchives client for unit-style tests."""
    client = MockClient()
    yield client
    client.expect_clear()


@pytest.fixture
def backend_client(backend: Any) -> LA.Client:
    """Return a real client wired to the mock backend session shim."""
    client = LA.Client("https://test-labapi.test", "test", "test")
    client.session = BackendSession(backend)
    return client
