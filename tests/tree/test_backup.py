"""Unit tests for Notebook.backup()."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

import labapi as LA
from labapi.client import StreamingResponse
from labapi.exceptions import ApiError


def _mock_stream(client, chunks: list[bytes]) -> Mock:
    """Replace client.stream_api_get with a mock yielding ``chunks``."""
    response = Mock()
    response.iter_content.return_value = list(chunks)
    stream = Mock(return_value=StreamingResponse(response))
    client.stream_api_get = stream
    return stream


def test_backup_streams_archive_to_path(client, notebook: LA.Notebook, tmp_path):
    """backup() streams the archive to a path and calls the backup endpoint."""
    stream = _mock_stream(client, [b"7z\xbc\xaf", b"payload"])

    dest = tmp_path / "nested" / "notebook.7z"
    result = notebook.backup(dest)

    assert result == dest
    assert dest.read_bytes() == b"7z\xbc\xafpayload"
    stream.assert_called_once_with(
        "notebooks/notebook_backup", uid="testid1", nbid="testnb1"
    )


def test_backup_optional_params_mapped(client, notebook: LA.Notebook, tmp_path):
    """include_attachments/as_json map to the API's no_attachments/json flags."""
    stream = _mock_stream(client, [b"data"])

    notebook.backup(tmp_path / "nb.7z", include_attachments=False, as_json=True)

    stream.assert_called_once_with(
        "notebooks/notebook_backup",
        uid="testid1",
        nbid="testnb1",
        json="true",
        no_attachments="true",
    )


def test_backup_surfaces_missing_rights_error(client, notebook: LA.Notebook, tmp_path):
    """A 4547 owner-sign-in error is re-raised with actionable guidance."""
    raw_error = ApiError("[4547] does not have rights", 4547)
    client.stream_api_get = Mock(side_effect=raw_error)

    with pytest.raises(ApiError) as exc_info:
        notebook.backup(tmp_path / "nb.7z")

    assert exc_info.value.error_code == 4547
    assert "notebook owner's sign-in" in str(exc_info.value)
    assert exc_info.value.__cause__ is raw_error
    assert not (tmp_path / "nb.7z").exists()


def test_backup_propagates_other_errors(client, notebook: LA.Notebook, tmp_path):
    """Non-4547 API errors pass through unchanged."""
    raw_error = ApiError("[5000] other", 5000)
    client.stream_api_get = Mock(side_effect=raw_error)

    with pytest.raises(ApiError) as exc_info:
        notebook.backup(tmp_path / "nb.7z")

    assert exc_info.value is raw_error
