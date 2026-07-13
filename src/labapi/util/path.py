"""Path utilities for navigating and creating LabArchives tree nodes."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from enum import Enum
from typing import TYPE_CHECKING, NewType, overload

from typing_extensions import override

from labapi.exceptions import PathError

if TYPE_CHECKING:
    from labapi.tree.mixins import AbstractBaseTreeNode


EscapedSegment = NewType("EscapedSegment", str)
UnescapedSegment = NewType("UnescapedSegment", str)


class _LexerState(Enum):
    BASE = 1
    ESCAPE = 2


def _lexe(*paths: str) -> tuple[Sequence[UnescapedSegment], bool]:
    segments: list[UnescapedSegment] = []
    segment = ""
    lexe_state = _LexerState.BASE

    path = "/".join(paths)

    for char in path:
        match char, lexe_state:
            case "\\", _LexerState.BASE:
                lexe_state = _LexerState.ESCAPE
            case "/", _LexerState.BASE:
                if len(segment) > 0:
                    segments.append(UnescapedSegment(segment))
                    segment = ""
            case _, _LexerState.BASE:
                segment += char
            case _, _LexerState.ESCAPE:
                segment += char
                lexe_state = _LexerState.BASE

    if lexe_state == _LexerState.ESCAPE:
        raise PathError("Path cannot end with an escape character", path=path)

    if len(segment):
        segments.append(UnescapedSegment(segment))

    return segments, path.startswith("/")


def _canonicalize(
    *path: UnescapedSegment, from_root: bool
) -> Sequence[UnescapedSegment]:
    assert not isinstance(path, str)

    canonical: list[UnescapedSegment] = []

    for segment in path:
        match segment:
            case ".":
                continue
            case ".." if len(canonical) == 0:
                if not from_root:
                    canonical.append(segment)
            case ".." if canonical[-1] == "..":
                canonical.append(segment)
            case "..":
                canonical.pop()
            case _:
                canonical.append(segment)

    return canonical


class NotebookPath(Sequence[UnescapedSegment]):
    r"""A structured path referencing a location in the notebook tree.

    Supports absolute and relative paths, plus ``..`` parent navigation.

    Empty segments and ``.`` are discarded; ``..`` collapses the preceding
    segment, or is kept at the root of a relative path.

    If a node name contains a literal ``/``, write it as ``\/`` in a path
    string, e.g. ``r"Reports\/2024"``. Iteration, indexing, :attr:`name`, and
    :attr:`parts` return node names. ``str()`` adds escapes back so the result
    can be parsed again.

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
        part: NotebookPath | AbstractBaseTreeNode | EscapedSegment,
        *parts: EscapedSegment,
        parent: NotebookPath | AbstractBaseTreeNode | None = None,
    ):
        r"""Construct a ``NotebookPath``.

        Additional ``parts`` are appended to ``part``.

        :param part: A tree node creates an absolute path, a ``NotebookPath``
            is copied, and a string is parsed as path syntax.
        :param parts: Additional path strings appended after ``part``. ``/``
            separates segments unless it is escaped as ``\/``.
        :param parent: Absolute path or node used later to resolve a relative
            string path. Must be absolute.
        :raises PathError: If ``parent`` is not absolute.
        """
        self._parent: NotebookPath | None = None
        self._parts: Sequence[UnescapedSegment] = ()
        self._absolute: bool = False
        other_parts, _ = _lexe(*parts)

        if parent is not None:
            _parent = NotebookPath(parent)
            if not _parent.is_absolute():
                raise PathError(
                    "Parent path must be absolute",
                    path=str(part),
                    parent=str(_parent),
                )
        else:
            _parent = None

        if isinstance(part, NotebookPath):
            self._parts = _canonicalize(
                *part._parts, *other_parts, from_root=part._absolute
            )
            self._absolute = part._absolute
            self._parent = part._parent
        elif isinstance(part, str):
            lexed, is_absolute = _lexe(part)
            self._absolute = is_absolute and parent is None
            self._parts = _canonicalize(*lexed, *other_parts, from_root=self._absolute)
        else:
            self._parts = _canonicalize(
                *NotebookPath._of_node(part), *other_parts, from_root=True
            )
            self._absolute = True

        if _parent is not None:
            self._parent = _parent

    def __truediv__(self, other: str | NotebookPath) -> NotebookPath:
        """Append a segment or another path using the ``/`` operator.

        When ``other`` is a string it is appended as a new segment. When
        ``other`` is a relative ``NotebookPath`` it is resolved against
        ``self``; when it is absolute it is returned as-is.

        :param other: A path segment string or another ``NotebookPath``.
        :returns: A new ``NotebookPath`` with ``other`` appended or resolved.
        """
        if isinstance(other, str):
            return NotebookPath(self, EscapedSegment(other))
        return other.resolve(self)

    @staticmethod
    def escape(*parts: UnescapedSegment) -> tuple[EscapedSegment, ...]:
        """Add path escapes."""
        return tuple(
            EscapedSegment(part.replace("\\", "\\\\").replace("/", r"\/"))
            for part in parts
        )

    @staticmethod
    def unescape(part: EscapedSegment) -> UnescapedSegment:
        """Remove path escapes."""
        segment = ""
        lexe_state = _LexerState.BASE

        for char in part:
            match char, lexe_state:
                case "\\", _LexerState.BASE:
                    lexe_state = _LexerState.ESCAPE
                case _, _LexerState.BASE:
                    segment += char
                case _, _LexerState.ESCAPE:
                    segment += char
                    lexe_state = _LexerState.BASE

        return UnescapedSegment(segment)

    def to_string(self, escape=False) -> str:
        r"""Return the path as a slash-separated string.

        By default, names are joined as-is. Pass ``escape=True`` to match
        ``str(path)``.

        :returns: Examples include ``"/Experiments/2024"`` and
            ``"2024/Results"``.
        """
        parts = self.escape(*self._parts) if escape else self._parts
        if self._absolute:
            return f"/{'/'.join(parts)}"

        return "/".join(parts)

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
        if self._parent is None:
            if self.is_absolute():
                return self

            if parent is not None:
                return NotebookPath(
                    parent.resolve() if recurse else parent,
                    *self.escape(*self._parts),
                )

            raise PathError(
                "Cannot resolve relative path without an absolute parent",
                path=str(self),
            )

        return NotebookPath(self._parent, *self.escape(*self._parts)).resolve(
            parent, recurse
        )

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
            remaining = self.escape(*self[len(other) :])
            return (
                NotebookPath(*remaining)
                if remaining
                else NotebookPath(EscapedSegment(""))
            )

        p_origin = other.resolve()
        p_endpoint = self.resolve(other)

        remaining = list(p_endpoint[len(p_origin) :])
        return (
            NotebookPath(*self.escape(*remaining), parent=p_origin)
            if remaining
            else NotebookPath(EscapedSegment(""), parent=p_origin)
        )

    @property
    def name(self) -> UnescapedSegment:
        """The final node name.

        Returns ``"."`` for an empty path.
        """
        if len(self._parts):
            return self._parts[-1]
        return UnescapedSegment(".")

    @property
    def parts(self) -> Sequence[UnescapedSegment]:
        """All node names except the last one.

        Analogous to the parent directory in a file path.
        """
        return tuple(self._parts[:-1])

    @property
    def parent(self) -> NotebookPath:
        """The parent path (all segments except the last).

        Resolves the path first, then appends ``..`` to obtain the parent.

        :returns: An absolute ``NotebookPath`` pointing to the parent location.
        """
        if len(self) == 0 and self._absolute:
            return self.resolve() / ".."
        return self / ".."

    @override
    def __iter__(self) -> Iterator[UnescapedSegment]:
        """Iterate over node names in order."""
        return iter(self._parts)

    @override
    def __len__(self) -> int:
        """Return the number of segments in the path."""
        return len(self._parts)

    @overload
    def __getitem__(self, idx: int) -> UnescapedSegment: ...

    @overload
    def __getitem__(self, idx: slice) -> Sequence[UnescapedSegment]: ...

    @override
    def __getitem__(
        self, idx: int | slice
    ) -> UnescapedSegment | Sequence[UnescapedSegment]:
        """Return node name(s)."""
        return self._parts[idx]

    @override
    def __hash__(self) -> int:
        """Hash the resolved path so equal paths hash equally.

        Mirrors ``__eq__``, which compares resolved paths. An unresolvable
        relative path (no parent anchor) falls back to its unresolved state;
        such a path is only ever equal to itself.
        """
        try:
            resolved = self.resolve()
        except PathError:
            return hash((self._absolute, tuple(self._parts)))
        return hash((resolved._absolute, tuple(resolved._parts)))

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
        try:
            a = self.resolve()
            b = other.resolve()
            return a._absolute == b._absolute and a._parts == b._parts
        except PathError:
            return False

    @override
    def __repr__(self) -> str:
        """Return a developer-readable representation, e.g. ``NotebookPath('/a/b')``."""
        return f"{type(self).__name__}({self.to_string(escape=True)!r})"

    @override
    def __str__(self) -> str:
        """Return a reusable path string; use ``to_string()`` for raw names."""
        return self.to_string(escape=True)

    @staticmethod
    def _of_node(a: AbstractBaseTreeNode) -> Sequence[UnescapedSegment]:
        """Return the ordered list of ancestor names from the notebook root to ``a``.

        Walks ``a.parent`` until the root is reached, building the segment list
        from the bottom up.

        :param a: The tree node to derive a path for.
        :returns: A sequence of name strings representing the path from root to
            ``a``, not including the root notebook itself.
        """
        stack: list[UnescapedSegment] = []

        curr = a

        while curr is not curr.root:
            stack.append(UnescapedSegment(curr.name))
            curr = curr.parent

        return stack[::-1]
