"""Attachment data structure."""

from __future__ import annotations

import shutil
import tempfile
from mimetypes import guess_type
from os import PathLike
from pathlib import Path
from typing import IO, Any, BinaryIO, Protocol, TypeAlias, TypeGuard, cast

from typing_extensions import Buffer

# NOTE: from Pylance
# Unfortunately PEP 688 does not allow us to distinguish read-only
# from writable buffers. We use these aliases for readability for now.
# Perhaps a future extension of the buffer protocol will allow us to
# distinguish these cases in the type system.
# Same as WriteableBuffer, but also includes read-only buffer types (like bytes).
ReadableBuffer: TypeAlias = Buffer


class NamedBinaryIO(Protocol):
    """Binary file-like object with a ``name`` attribute."""

    @property
    def name(self) -> str:
        """Return the local filename for this stream."""
        ...

    def read(self, size: int = -1, /) -> bytes:
        """Read bytes from the stream."""
        ...

    def write(self, data: ReadableBuffer, /) -> int:
        """Write bytes to the stream."""
        ...

    def seek(self, offset: int, whence: int = 0, /) -> int:
        """Move the stream cursor."""
        ...

    def tell(self) -> int:
        """Return the current stream cursor position."""
        ...

    def close(self) -> None:
        """Close the stream."""
        ...

    def seekable(self) -> bool:
        """Return whether the stream supports random access."""
        ...


def is_strpathlike(obj: Any) -> TypeGuard[PathLike[str]]:
    """Return whether ``obj`` is a path-like object with a string path."""
    return isinstance(obj, PathLike) and isinstance(obj.__fspath__(), str)


class Attachment:
    """Represents an attachment file with associated metadata.

    This class wraps a file-like object (such as BytesIO or TemporaryFile) along
    with metadata like MIME type, filename, and caption.

    .. note::
       Write operations to the backing buffer need explicit syncing with the server.
    """

    @staticmethod
    def _is_seekable(stream: IO[bytes] | NamedBinaryIO) -> bool:
        """Return whether ``stream`` supports random access."""
        seekable = getattr(stream, "seekable", None)
        if callable(seekable):
            try:
                return bool(seekable())
            except (OSError, ValueError):
                return False

        seek = getattr(stream, "seek", None)
        tell = getattr(stream, "tell", None)
        if not callable(seek) or not callable(tell):
            return False

        try:
            position = tell()
            seek(position)
        except (OSError, TypeError, ValueError):
            return False

        return True

    @staticmethod
    def from_file(file: NamedBinaryIO | PathLike[str] | str) -> Attachment:
        """Create an attachment by cloning a file object or filesystem path.

        The content of the provided file is copied into a temporary buffer,
        making the Attachment independent of the original file's state. If a
        filesystem path is provided, ``labapi`` opens it in binary mode before
        cloning it. The MIME type is automatically guessed from the local file
        name. If the MIME type cannot be determined, it defaults to
        ``"application/octet-stream"``. File-like inputs must support random
        access so ``labapi`` can rewind them, checked via ``seekable()`` when
        present, otherwise via working ``seek()`` and ``tell()`` methods.

        :param file: The filesystem path or file object to create an
                     attachment from.
        :returns: A new Attachment object wrapping a clone of the file.
        """
        if isinstance(file, str) or is_strpathlike(file):
            with Path(file).open("rb") as stream:
                return Attachment.from_file(cast(NamedBinaryIO, stream))

        assert not isinstance(file, PathLike)

        if not Attachment._is_seekable(file):
            raise ValueError("Attachment.from_file requires a seekable file object")

        remote_filename = Path(file.name).name
        mime_type = guess_type(file.name)[0] or "application/octet-stream"
        original_position = file.tell()

        # Create a spooled temporary file as the new backing buffer.
        # It stays in memory until it reaches 4MB, then rolls over to disk.
        backing: BinaryIO = cast(
            BinaryIO,
            tempfile.SpooledTemporaryFile(max_size=4 * 1024 * 1024, mode="w+b"),  # noqa: SIM115
        )
        try:
            file.seek(0)
            shutil.copyfileobj(file, backing)
        finally:
            file.seek(original_position)
        backing.seek(0)

        return Attachment(
            backing,
            mime_type,
            remote_filename,
            caption=f"API-uploaded {mime_type} file.",
        )

    def __init__(
        self,
        backing: IO[bytes],
        mime_type: str,
        filename: str,
        caption: str,
    ):
        """Initialize an attachment wrapper.

        :param backing: The file-like object that contains the attachment data.
                        Can be a BufferedRandom, BufferedReader, BytesIO, or TemporaryFile.
        :param mime_type: The MIME type of the attachment (e.g., "image/png", "application/pdf").
        :param filename: The filename of the attachment.
        :param caption: A descriptive caption for the attachment.
        """
        self._backing = backing
        if self._is_seekable(self._backing):
            self._backing.seek(0)

        self._mime_type = mime_type
        self._filename = filename
        self._caption = caption

    def __getattr__(self, attr: str) -> Any:
        """Delegate unknown attributes to the backing file object.

        This allows the Attachment to behave like the underlying file object
        for operations like read(), write(), etc.

        :param attr: The attribute name to access on the backing object.
        :returns: The attribute value from the backing object.
        :raises AttributeError: If the attribute does not exist on the backing object.
        """
        return getattr(self._backing, attr)

    def read(self, size: int = -1, /) -> bytes:
        """Read bytes from the backing attachment stream."""
        return self._backing.read(size)

    def write(self, data: ReadableBuffer, /) -> int:
        """Write bytes to the backing attachment stream."""
        return self._backing.write(data)

    def seek(self, offset: int, whence: int = 0, /) -> int:
        """Move the backing stream cursor."""
        return self._backing.seek(offset, whence)

    def tell(self) -> int:
        """Return the current backing stream cursor position."""
        return self._backing.tell()

    def close(self) -> None:
        """Close the backing attachment stream."""
        self._backing.close()

    def seekable(self) -> bool:
        """Return whether the backing stream supports random access."""
        return self._is_seekable(self._backing)

    @property
    def filename(self) -> str:
        """Return the attachment filename.

        :returns: The filename.
        """
        return self._filename

    @property
    def mime_type(self) -> str:
        """Return the attachment MIME type.

        :returns: The MIME type (e.g., "image/png", "application/pdf").
        """
        return self._mime_type

    @property
    def caption(self) -> str:
        """Return the attachment caption.

        :returns: The caption text.
        """
        return self._caption
