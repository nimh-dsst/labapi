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


def _failing_stream(client) -> Mock:
    """Replace stream_api_get with a stream that raises partway through."""

    def chunks():
        yield b"partial"
        raise RuntimeError("network drop")

    response = Mock()
    response.iter_content.return_value = chunks()
    stream = Mock(return_value=StreamingResponse(response))
    client.stream_api_get = stream
    return stream


def test_backup_interrupted_preserves_existing_archive(
    client, notebook: LA.Notebook, tmp_path
):
    """A mid-download failure must not truncate the existing archive or leave a partial."""
    dest = tmp_path / "nb.7z"
    dest.write_bytes(b"OLD-GOOD-ARCHIVE")
    _failing_stream(client)

    with pytest.raises(RuntimeError, match="network drop"):
        notebook.backup(dest)

    assert dest.read_bytes() == b"OLD-GOOD-ARCHIVE"
    assert list(tmp_path.glob("*.part")) == []


def test_backup_closes_stream_when_mkdir_fails(client, notebook: LA.Notebook, tmp_path):
    """If destination-directory creation fails, the HTTP stream is still closed."""
    blocker = tmp_path / "blocker"
    blocker.write_bytes(b"i am a file, not a directory")
    response = Mock()
    response.iter_content.return_value = [b"data"]
    client.stream_api_get = Mock(return_value=StreamingResponse(response))

    with pytest.raises(FileExistsError):
        notebook.backup(blocker / "nb.7z")

    response.close.assert_called_once_with()
