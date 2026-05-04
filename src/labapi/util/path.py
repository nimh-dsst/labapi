"""Path utilities for navigating and creating LabArchives tree nodes."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from enum import Enum
from typing import TYPE_CHECKING, overload

from typing_extensions import override

from labapi.exceptions import PathError

if TYPE_CHECKING:
    from labapi.tree.mixins import AbstractBaseTreeNode


class _LexerState(Enum):
    BASE = 1
    ESCAPE = 2


def _lexe(*paths: str) -> tuple[Sequence[str], bool]:
    segments: list[str] = []
    segment = ""
    lexe_state = _LexerState.BASE

    path = "/".join(paths)

    for char in path:
        match char, lexe_state:
            case "\\", _LexerState.BASE:
                lexe_state = _LexerState.ESCAPE
            case "/", _LexerState.BASE:
                if len(segment) > 0:
                    segments.append(segment)
                    segment = ""
            case _, _LexerState.BASE:
                segment += char
            case _, _LexerState.ESCAPE:
                segment += char
                lexe_state = _LexerState.BASE

    if len(segment):
        segments.append(segment)

    return segments, path.startswith("/")


def _canonicalize(*path: str, from_root: bool) -> Sequence[str]:
    assert not isinstance(path, str)

    canonical: list[str] = []

    for segment in path:
        match segment:
            case ".":
                continue
            case ".." if len(canonical) == 0:
                if not from_root:
                    canonical.append("..")
            case ".." if canonical[-1] == "..":
                canonical.append("..")
            case "..":
                canonical.pop()
            case _:
                canonical.append(segment)

    return canonical


class NotebookPath(Sequence[str]):
    """A structured path referencing a location in the notebook tree.

    Behaves like a sequence of path segments (strings) and supports Unix-style
    path semantics including absolute/relative paths and ``..`` parent navigation.

    Paths can be constructed from a tree node, another ``NotebookPath``, or raw
    slash-separated strings. Segments are normalised on construction: empty
    segments and ``.`` are discarded, and ``..`` collapses the preceding segment
    (or is kept literally when at the root of a relative path).

    Examples::

        # From a tree node (always absolute)
        path = NotebookPath(folder)             # e.g. /Experiments/2024

        # From a string
        path = NotebookPath("/Experiments/2024")  # absolute
        path = NotebookPath("2024/Results")        # relative

        # Combine with /
        path = NotebookPath(notebook) / "Experiments" / "2024"
    """

    def __init__(
        self,
        part: NotebookPath | AbstractBaseTreeNode | str,
        *parts: str,
        parent: NotebookPath | AbstractBaseTreeNode | None = None,
    ):
        """Construct a ``NotebookPath``.

        The first argument ``part`` sets the base of the path; any additional
        positional ``parts`` are appended as extra segments.

        :param part: The base of the path. Pass a tree node to create an
            absolute path rooted at that node's location, a ``NotebookPath``
            to extend it, or a slash-separated string (absolute strings start
            with ``/``; others are relative).
        :param parts: Additional slash-separated path segments appended after
            ``part``. Segments are split on ``/`` and normalised.
        :param parent: An absolute path (or node) that anchors a relative
            string path for later resolution. Must be absolute.
        :raises PathError: If ``parent`` is not absolute.
        """
        self._parent: NotebookPath | None = None
        self._parts: Sequence[str] = ()
        self._absolute: bool = False

        if parent is not None:
            self._parent = NotebookPath(parent)
            if not self._parent.is_absolute():
                raise PathError(
                    "Parent path must be absolute",
                    path=str(part),
                    parent=str(self._parent),
                )
        else:
            self._parent = None

        other_parts, _ = _lexe(*parts)

        if isinstance(part, NotebookPath):
            self._parts = _canonicalize(
                *part._parts, *other_parts, from_root=part._absolute
            )
            self._absolute = part._absolute
            self._parent = part._parent
        elif isinstance(part, str):
            lexed, is_absolute = _lexe(part)
            self._absolute = is_absolute and self._parent is None
            self._parts = _canonicalize(*lexed, *other_parts, from_root=self._absolute)
        else:
            self._parts = _canonicalize(
                *NotebookPath._of_node(part), *other_parts, from_root=True
            )
            self._absolute = True

    def __truediv__(self, other: str | NotebookPath) -> NotebookPath:
        """Append a segment or another path using the ``/`` operator.

        When ``other`` is a string it is appended as a new segment. When
        ``other`` is a relative ``NotebookPath`` it is resolved against
        ``self``; when it is absolute it is returned as-is.

        :param other: A path segment string or another ``NotebookPath``.
        :returns: A new ``NotebookPath`` with ``other`` appended or resolved.
        """
        if isinstance(other, str):
            return NotebookPath(self, other)
        return other.resolve(self)

    def to_string(self) -> str:
        """Return the path as a slash-separated string.

        Absolute paths are prefixed with ``/``; relative paths are not.

        :returns: The string representation of this path (e.g.
            ``"/Experiments/2024"`` or ``"2024/Results"``).
        """
        if self._absolute:
            return f"/{'/'.join(self._parts)}"

        return "/".join(self._parts)

    def is_absolute(self) -> bool:
        """Return whether this path is absolute.

        An absolute path is rooted at the notebook level and begins with
        ``/`` in its string form.

        :returns: ``True`` if the path is absolute, ``False`` if relative.
        """
        return self._absolute

    def resolve(
        self, parent: NotebookPath | None = None, recurse: bool = False
    ) -> NotebookPath:
        """Return an absolute version of this path.

        If the path is already absolute it is returned unchanged. Otherwise
        the path is resolved against ``parent`` (if given) or against the
        ``parent`` anchor stored at construction time.

        :param parent: An absolute path to resolve against. Ignored when the
            path is already absolute or has a stored parent anchor.
        :param recurse: If ``True``, ``parent`` itself is resolved before use.
        :returns: A new absolute ``NotebookPath``.
        :raises PathError: If the path is relative and no parent is available
            to resolve against.
        """
        if self.is_absolute():
            return self
        if self._parent is None:
            if parent is not None:
                return NotebookPath(
                    parent.resolve() if recurse else parent, *self._parts
                )

            raise PathError(
                "Cannot resolve relative path without an absolute parent",
                path=str(self),
            )

        return NotebookPath(self._parent, *self._parts)

    def startswith(self, other: NotebookPath) -> bool:
        """Return whether this path starts with another path's segments.

        Compares raw segments without resolving either path.

        :param other: The prefix path to test against.
        :returns: ``True`` if the leading segments of this path equal all
            segments of ``other``.
        """
        if len(self) < len(other):
            return False
        return self[: len(other)] == other[: len(other)]

    def is_relative_to(self, other: NotebookPath | AbstractBaseTreeNode) -> bool:
        """Return whether this path is located inside ``other``.

        Unanchored relative paths are considered to be relative to any
        absolute path.

        :param other: The candidate ancestor path or tree node.
        :returns: ``True`` if this path is equal to or below ``other``.
        """
        if not isinstance(other, NotebookPath):
            other = NotebookPath(other)

        if not other._absolute and other._parent is None:
            if not self._absolute and self._parent is None:
                return self.startswith(other)
            return False

        if not self._absolute and self._parent is None:
            return True

        return self.resolve().startswith(other.resolve())

    def relative_to(self, other: NotebookPath | AbstractBaseTreeNode) -> NotebookPath:
        """Return this path made relative to ``other``.

        The result is a new relative ``NotebookPath`` whose ``parent`` anchor
        is set to the resolved form of ``other``, so it can be resolved back
        to an absolute path later.

        :param other: The ancestor path or tree node to relativise against.
        :returns: A relative ``NotebookPath`` from ``other`` to this path.
        :raises PathError: If this path is not located inside ``other``.
        """
        if not isinstance(other, NotebookPath):
            other = NotebookPath(other)

        if not self.is_relative_to(other):
            raise PathError(
                f'Cannot compute relative path: "{self}" is outside of "{other}"',
                path=str(self),
                parent=str(other),
            )

        if not other._absolute and other._parent is None:
            return NotebookPath(*self[len(other) :])

        p_origin = other.resolve()
        p_endpoint = self.resolve(other)

        remaining = list(p_endpoint[len(p_origin) :])
        return (
            NotebookPath(*remaining, parent=p_origin)
            if remaining
            else NotebookPath("", parent=p_origin)
        )

    @property
    def name(self) -> str:
        """The final segment of the path.

        Equivalent to the node's display name when the path was built from a
        tree node. Returns ``"."`` for an empty path.

        :returns: The last path segment, or ``"."`` if the path is empty.
        """
        if len(self._parts):
            return self._parts[-1]
        return "."

    @property
    def parts(self) -> Sequence[str]:
        """All path segments except the last one.

        Analogous to the parent directory in a file path.

        :returns: A sequence of segment strings, empty if the path has only
            one segment.
        """
        return self._parts[:-1]

    @property
    def parent(self) -> NotebookPath:
        """The parent path (all segments except the last).

        Resolves the path first, then appends ``..`` to obtain the parent.

        :returns: An absolute ``NotebookPath`` pointing to the parent location.
        """
        return self.resolve() / ".."

    @override
    def __iter__(self) -> Iterator[str]:
        """Iterate over the path segments in order."""
        return iter(self._parts)

    @override
    def __len__(self) -> int:
        """Return the number of segments in the path."""
        return len(self._parts)

    @overload
    def __getitem__(self, idx: int) -> str: ...

    @overload
    def __getitem__(self, idx: slice) -> Sequence[str]: ...

    @override
    def __getitem__(self, idx: int | slice) -> str | Sequence[str]:
        """Return the segment at ``idx``, or a sub-sequence for a slice."""
        return self._parts[idx]

    @override
    def __hash__(self) -> int:
        """Hash based on absoluteness, segments, and parent anchor."""
        return hash((self._absolute, tuple(self._parts)))

    @override
    def __eq__(self, other: object) -> bool:
        """Return ``True`` if ``other`` has the same path semantics.

        Equality compares absoluteness, normalized segments, and any stored
        parent anchor.
        """
        if self is other:
            return True
        if not isinstance(other, NotebookPath):
            return False
        return (
            self._absolute == other._absolute
            and self._parts == other._parts
            and self._parent == other._parent
        )

    @override
    def __repr__(self) -> str:
        """Return a developer-readable representation, e.g. ``NotebookPath('/a/b')``."""
        return f"{type(self).__name__}({self.to_string()!r})"

    @override
    def __str__(self) -> str:
        """Return the slash-separated string form of the path."""
        return self.to_string()

    @staticmethod
    def _of_node(a: AbstractBaseTreeNode) -> Sequence[str]:
        """Return the ordered list of ancestor names from the notebook root to ``a``.

        Walks ``a.parent`` until the root is reached, building the segment list
        from the bottom up.

        :param a: The tree node to derive a path for.
        :returns: A sequence of name strings representing the path from root to
            ``a``, not including the root notebook itself.
        """
        stack: list[str] = []

        curr = a

        while curr is not curr.root:
            stack.append(curr.name)
            curr = curr.parent

        return stack[::-1]
