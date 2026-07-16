"""Tree Mixins Module.

This module defines abstract base classes and mixins that form the hierarchical
structure of LabArchives notebooks, directories, and pages.
"""

from __future__ import annotations

import time
import warnings
from abc import ABC, abstractmethod
from collections.abc import (
    ItemsView,
    Iterator,
    KeysView,
    Mapping,
    MutableSequence,
    Sequence,
    ValuesView,
)
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Literal, TypeVar, cast, overload

from typing_extensions import Self, override

from labapi.exceptions import (
    ExtractionError,
    NodeExistsError,
    TraversalError,
    TreeChildParseError,
)
from labapi.util import (
    IdIndex,
    IdOrNameIndex,
    Index,
    InsertBehavior,
    NameIndex,
    NotebookPath,
    extract_etree,
    to_bool,
)
from labapi.util.path import EscapedSegment

if TYPE_CHECKING:
    from labapi.user import User

    from .directory import NotebookDirectory
    from .page import NotebookPage


class HasNameMixin:
    """A mixin class that provides a `name` attribute for tree nodes.

    Classes inheriting from this mixin are expected to have a `_name` instance
    variable.
    """

    def __init__(self, name: str):
        """Initialize the mixin with a node name.

        :param name: The name of the tree node.
        """
        super().__init__()
        self._name = name

    @property
    def name(self) -> str:
        """Return the tree node name.

        :returns: The name of the node.
        """
        return self._name


class AbstractBaseTreeNode(ABC, HasNameMixin):
    """Abstract base class for any node within the LabArchives tree structure.

    This class provides properties and methods common to all
    tree nodes, such as ID, name, references to parent and root, and the
    associated user.

    :param tree_id: The unique identifier for this node within the LabArchives tree.
    :param name: The display name of the node.
    :param root: The root node of the tree (e.g., the Notebook).
    :param parent: The parent node of this node in the tree.
    :param user: The authenticated user associated with this node.
    """

    def __init__(
        self,
        tree_id: str,
        name: str,
        root: AbstractTreeContainer,
        parent: AbstractTreeContainer,
        user: User,
    ):
        """Initialize a tree node with IDs, hierarchy pointers, and user state."""
        super().__init__(name)
        self._root: AbstractTreeContainer = root
        self._parent: AbstractTreeContainer = parent
        self._tree_id: str = tree_id
        self._user = user
        self._has_path = False
        self._path: NotebookPath

    @property
    def root(self) -> AbstractTreeContainer:
        """Return the root node of the tree.

        :returns: The root tree container.
        """
        return self._root

    @property
    def parent(self) -> AbstractTreeContainer:
        """Return this node's parent container.

        :returns: The parent tree container.
        """
        return self._parent

    @property
    def user(self) -> User:
        """Return the authenticated user associated with this node.

        :returns: The user object.
        """
        return self._user

    @property
    @abstractmethod
    def id(self) -> str:
        """Return the node identifier.

        :returns: The node's ID.
        """
        return self.tree_id

    @property
    def tree_id(self) -> str:
        """Return the node identifier within the LabArchives tree.

        Equal to `id` for all nodes except the Notebook root, whose `tree_id`
        is the sentinel "0" while `id` is the notebook ID.

        :returns: The tree ID of the node.
        """
        return self._tree_id

    @property
    def path(self) -> NotebookPath:
        """Return the cached absolute path for this node."""
        if not self._has_path:
            self._path = NotebookPath(self)
            self._has_path = True

        return self._path

    def _invalidate_path(self) -> None:
        """Clear cached paths for this node and any loaded descendants."""
        self._has_path = False

        if isinstance(self, AbstractTreeContainer):
            for child in self._children:
                child._invalidate_path()

    @abstractmethod
    def is_dir(self) -> bool:
        """Return whether this node is a directory.

        :returns: True if the node is a directory, False otherwise.
        """
        return False

    @abstractmethod
    def refresh(self) -> Self:
        """Refresh this node's cached data from the LabArchives API.

        This method updates the node's properties (such as name, ID, and children)
        by fetching the latest data from the server. This is useful when the
        node's state may have changed externally.
        """
        raise NotImplementedError()

    def traverse(self, path: str | NotebookPath) -> AbstractBaseTreeNode:
        """Traverse the notebook tree and return the node at ``path``.

        String path segments should be separated by '/'. Each segment is treated
        as a name to look up in the current container. Paths starting with '/'
        are absolute (relative to the notebook root), while paths without a
        leading '/' are relative to the current container.

        Special path segments:
        - '..' navigates to the parent container

        .. note::
           - When multiple children have the same name, this method returns the first match.

        .. warning::
           Nodes with names that are literally '..' cannot be accessed via
           this method, as '..' is reserved for parent navigation.

        :param path: The slash-separated path to the desired node (e.g., "My Folder/My Page" or "/Folder/Subfolder/Page").
        :returns: The :class:`~labapi.tree.mixins.AbstractBaseTreeNode` found
                  at the specified path.
        :raises TraversalError: If traversal cannot continue through a segment.
        """
        canonical = (
            NotebookPath(EscapedSegment(path)) if isinstance(path, str) else path
        )
        canonical = canonical.resolve(self.path)

        curr = self.root

        parsed_segments: list[str] = []

        for segment in canonical:
            parsed_segments.append(segment)
            if segment == "..":
                curr = curr.parent
            elif isinstance(curr, AbstractTreeContainer):
                try:
                    curr = curr[segment]
                except KeyError as exc:
                    resolved_parent = (
                        "/"
                        if len(parsed_segments) == 1
                        else f"/{'/'.join(parsed_segments[:-1])}"
                    )
                    available_children = sorted(node.name for node in curr.children)
                    raise TraversalError(
                        (
                            f'Unable to traverse "{canonical}" at segment "{segment}": '
                            f'child "{segment}" not found in "{resolved_parent}"'
                        ),
                        path=str(canonical),
                        segment=segment,
                        parent=resolved_parent,
                        available_children=available_children,
                    ) from exc
            else:
                resolved_parent = (
                    "/"
                    if len(parsed_segments) == 1
                    else f"/{'/'.join(parsed_segments[:-1])}"
                )
                raise TraversalError(
                    (
                        f'Unable to traverse "{canonical}" at segment "{segment}": '
                        f'"{"/".join(parsed_segments)}" is not a directory'
                    ),
                    path=str(canonical),
                    segment=segment,
                    parent=resolved_parent,
                )

        return curr

    def as_dir(self) -> AbstractTreeContainer:
        """Return this node cast to :class:`~labapi.tree.mixins.AbstractTreeContainer`.

        Use after checking :meth:`is_dir` to obtain a container-typed
        reference for static type checking.

        :returns: The node cast to an
                  :class:`~labapi.tree.mixins.AbstractTreeContainer`.
        :raises TypeError: If the node is not a directory (i.e., `is_dir()` returns `False`).
        """
        if self.is_dir():
            return cast(AbstractTreeContainer, self)

        raise TypeError("Node is not a directory")

    def as_page(self) -> NotebookPage:
        """Return this node cast to :class:`~labapi.tree.page.NotebookPage`.

        Use after checking :meth:`is_dir` to obtain a page-typed reference
        for static type checking.

        :returns: The node cast to a
                  :class:`~labapi.tree.page.NotebookPage`.
        :raises TypeError: If the node is not a page (i.e., `is_dir()` returns `True`).
        """
        if not self.is_dir():
            from . import page

            return cast(page.NotebookPage, self)

        raise TypeError("Node is not a page")


class AbstractTreeNode(AbstractBaseTreeNode):
    """Abstract base class for a non-container node within the LabArchives tree structure.

    This class extends :class:`AbstractBaseTreeNode` with functionalities for
    modifying the node's name, copying, moving, and deleting the node.
    """

    @HasNameMixin.name.setter  # type: ignore[attr-defined]
    def name(self, value: str) -> None:
        """Set the tree node name.

        This operation updates the node's name in LabArchives via an API call.

        :param value: The new name for the node.
        """
        self.user.api_get(
            "tree_tools/update_node",
            nbid=self.root.id,
            tree_id=self.tree_id,
            display_text=value,
        )

        self._name = value
        self._invalidate_path()

    @abstractmethod
    def copy_to(self, destination: AbstractTreeContainer) -> Self:
        """Copy this node into ``destination``.

        :param destination: The target container to copy the node to.
        :returns: A new instance of the copied node in the destination.
        """

    def move_to(self, destination: AbstractTreeContainer) -> Self:
        """Move this node into ``destination``.

        This operation updates the node's parent in LabArchives via an API call
        and updates the local tree structure.

        :param destination: The target container to move the node to.
        :returns: The instance of the moved node.
        """
        if destination is self:
            raise ValueError("Cannot move a node to itself")

        if isinstance(self, AbstractTreeContainer) and self.is_parent_of(destination):
            raise ValueError("Cannot move a directory into one of its descendants")

        if destination.root is not self.root:
            raise ValueError("Cannot move a node across notebooks")

        self._user.api_get(
            "tree_tools/update_node",
            nbid=self.root.id,
            tree_id=self.tree_id,
            parent_tree_id=destination.tree_id,
        )
        del self.parent._children[  # pyright: ignore[reportPrivateUsage]
            self.parent.children.index(self)
        ]  # This removes current node from old parent in-place
        self._parent = destination
        self.parent._children.append(self)  # pyright: ignore[reportPrivateUsage]
        # This adds current node to new parent in-place

        self._invalidate_path()
        return self

    def delete(self) -> Self:
        """Move this node into the special ``API Deleted Items`` directory.

        If the "API Deleted Items" directory does not exist, it will be created.
        The node's name will be updated to reflect its deletion time.

        :returns: The instance of the deleted node.
        """
        api_deleted_items = self.root.dir("API Deleted Items")

        self.name = (
            f"{self.name} - Deleted at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        self.move_to(api_deleted_items)

        return self


T = TypeVar("T", bound=AbstractTreeNode)


class AbstractTreeContainer(
    AbstractBaseTreeNode,
    Mapping[IdOrNameIndex, AbstractBaseTreeNode | Sequence[AbstractBaseTreeNode]],
):
    """Abstract base class for a tree node that can contain other tree nodes (e.g., Notebooks, Directories).

    This class extends :class:`AbstractBaseTreeNode` and implements `collections.abc.Mapping`
    to allow access to its children by ID or name. It provides methods for managing
    its children, such as creating new pages or directories.
    """

    def __init__(
        self,
        tree_id: str,
        name: str,
        root: AbstractTreeContainer,
        parent: AbstractTreeContainer,
        user: User,
    ):
        """Initialize a tree container node.

        :param tree_id: The unique identifier for this container within the LabArchives tree.
        :param name: The display name of the container.
        :param root: The root node of the tree (e.g., the Notebook).
        :param parent: The parent node of this container in the tree.
        :param user: The authenticated user associated with this container.
        """
        super().__init__(tree_id, name, root, parent, user)
        self._children: MutableSequence[AbstractTreeNode] = []
        self._populated: bool = False

    @property
    def children(self) -> Sequence[AbstractTreeNode]:
        """Return a snapshot of this container's direct children.

        :returns: An immutable point-in-time sequence of
                  :class:`~labapi.tree.mixins.AbstractTreeNode` objects.
        """
        self._ensure_populated()
        return tuple(self._children)

    def _ensure_populated(self) -> None:
        """Load this container's children from the API if needed.

        If the children have not been loaded yet, it makes an API call to
        retrieve the tree level and populates the `_children` list.
        """
        from . import directory, page

        if not self._populated:
            xml_tree = self.user.api_get(
                "tree_tools/get_tree_level",
                nbid=self.root.id,
                parent_tree_id=self.tree_id,
            )

            nodes: list[AbstractTreeNode] = []

            for subtree in xml_tree.iterfind(".//level-node"):
                subtree_path = subtree.getroottree().getpath(subtree)
                try:
                    node = extract_etree(
                        subtree,
                        {
                            "is-page": to_bool,
                            "tree-id": str,
                            "display-text": str,
                        },
                    )
                except ExtractionError as err:
                    raise TreeChildParseError(
                        "Could not parse tree child at "
                        f"{subtree_path} for parent tree_id={self.tree_id!r}"
                    ) from err

                if not node["display-text"].strip():
                    raise TreeChildParseError(
                        "Could not parse tree child at "
                        f"{subtree_path} for parent tree_id={self.tree_id!r}: "
                        "display-text cannot be empty"
                    )

                args = (
                    node["tree-id"],
                    node["display-text"],
                    self.root,
                    self,
                    self._user,
                )

                if node["is-page"]:
                    nodes.append(page.NotebookPage(*args))
                else:
                    nodes.append(directory.NotebookDirectory(*args))

            self._children = nodes
            self._populated = True

    def __len__(self) -> int:
        """Return the number of direct children in this container.

        :returns: The count of direct child nodes.
        """
        self._ensure_populated()
        return len(self.children)

    def __iter__(self) -> Iterator[str]:
        """Iterate over direct child names in container order.

        :returns: An iterator yielding name strings.
        """
        return iter(node.name for node in self.children)

    def __contains__(self, key: object) -> bool:
        """Return whether the container contains the given key.

        :param key: The key or indexed selector to check for.
        :returns: True if the key is found and not empty, False otherwise.
        """
        try:
            return bool(self[key])  # type: ignore  # pyright: ignore[reportArgumentType]
        except (KeyError, TypeError):
            return False

    @override
    def keys(self) -> KeysView[str]:
        """Return a mapping-compatible view of child names."""
        self._ensure_populated()
        return KeysView({node.name: node for node in self.children})

    @override
    def items(self) -> ItemsView[str, AbstractBaseTreeNode]:
        """Return a mapping-compatible view of ``(name, child)`` pairs."""
        self._ensure_populated()
        return ItemsView({node.name: node for node in self.children})

    @override
    def values(self) -> ValuesView[AbstractBaseTreeNode]:
        """Return a mapping-compatible view of child nodes."""
        self._ensure_populated()
        return ValuesView({node.name: node for node in self.children})

    def all_keys(self) -> Sequence[str]:
        """Return child names in container order, preserving duplicates."""
        self._ensure_populated()
        return tuple([node.name for node in self.children])

    def all_items(self) -> Sequence[tuple[str, AbstractBaseTreeNode]]:
        """Return ``(name, child)`` pairs in container order, preserving duplicates."""
        self._ensure_populated()
        return tuple([(node.name, node) for node in self.children])

    def all_values(self) -> Sequence[AbstractBaseTreeNode]:
        """Return child nodes in container order, preserving duplicates."""
        self._ensure_populated()
        return tuple(self.children)

    @overload
    def __getitem__(self, key: str) -> AbstractBaseTreeNode: ...

    @overload
    def __getitem__(self, key: IdIndex) -> AbstractBaseTreeNode: ...

    @overload
    def __getitem__(self, key: NameIndex) -> Sequence[AbstractBaseTreeNode]: ...

    def __getitem__(
        self, key: IdOrNameIndex
    ) -> AbstractBaseTreeNode | Sequence[AbstractBaseTreeNode]:
        """Look up child nodes by name or indexed selector.

        - If `key` is a string, returns the first child with that name
          (raises :exc:`KeyError` if none match).
        - If `key` is a slice with start of :attr:`~labapi.util.Index.Id`
          (e.g., ``Index.Id:"some_id"``),
          it returns the child with the matching ID.
        - If `key` is a slice with start of :attr:`~labapi.util.Index.Name`
          (e.g., ``Index.Name:"some_name"``),
          it returns a list of all children with the matching name (as names are not unique).

        This method ensures the children are populated before attempting to access them.

        :param key: The index to use for accessing children.
        :returns: A single :class:`AbstractBaseTreeNode` or a sequence of :class:`AbstractBaseTreeNode`.
        :raises KeyError: If a single node is requested by ID or unique name and not found.
        """
        self._ensure_populated()

        match key:
            case slice(start=Index.Id, stop=val):
                for node in self.children:
                    if node.id == val:
                        return node
                raise KeyError(f'Node with id "{val}" not found in "{self.path}"')
            case slice(start=Index.Name, stop=val):
                return [node for node in self.children if node.name == val]
            case str():
                for node in self.children:
                    if node.name == key:
                        return node
                available_children = sorted(node.name for node in self.children)
                raise KeyError(
                    f'Child "{key}" not found in "{self.path}" (available: {available_children})'
                )
            case _:
                raise TypeError(
                    "Invalid key type. Use `str`, `Index.Id:<id>`, or `Index.Name:<name>`."
                )

    def is_parent_of(self, other: AbstractBaseTreeNode) -> bool:
        """Return whether this container is a strict ancestor of ``other``.

        This method returns ``True`` when ``other`` is a descendant of this
        container at any depth (direct child or deeper). A node is not
        considered a parent of itself.

        Nodes from different notebook roots are always considered unrelated,
        even if their relative paths happen to match.

        :param other: The node to test as a potential descendant.
        :returns: ``True`` if this container is an ancestor of ``other``,
            otherwise ``False``.
        """
        curr = other

        while curr is not curr.root:
            curr = curr.parent
            if curr is self:
                return True

        return False

    def _enumerate_nodes(
        self,
        *,
        depth: int = 1,
        timeout: timedelta = timedelta(seconds=5),
        _timeout: float | None = None,
        _current_depth: int = 0,
    ) -> Sequence[tuple[str, AbstractTreeNode]]:
        """Enumerate descendant paths paired with the node they resolved from."""
        current: MutableSequence[tuple[str, AbstractTreeNode]] = []

        if _current_depth >= depth:
            return current

        if _timeout is None:
            _timeout = time.monotonic() + timeout.total_seconds()

        self._ensure_populated()
        for child in self._children:
            name = child.name

            if time.monotonic() > _timeout:
                warnings.warn(
                    "Tree enumeration timed out before traversal completed; "
                    "returned paths are partial and may be unsafe for sync/export workflows.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                break

            current.append((name, child))

            try:
                container = child.as_dir()
                current.extend(
                    [
                        (f"{name}/{child_path}", descendant)
                        for child_path, descendant in container._enumerate_nodes(
                            _current_depth=_current_depth + 1,
                            depth=depth,
                            _timeout=_timeout,
                        )
                    ]
                )
            except TypeError:
                pass

        return current

    def enumerate_all(
        self,
        *,
        depth: int = 1,
        timeout: timedelta = timedelta(seconds=5),
    ) -> Sequence[str]:
        """Enumerate descendant directory and page paths.

        Returns relative path strings from the current container for all descendant
        nodes, including both directories and pages. Each path is relative to this
        container (e.g., "Folder/Page" or "Folder/Subfolder/Page").

        :param depth: The maximum depth to traverse. Default is 1 (only immediate children).
        :param timeout: The maximum time to spend enumerating children. Defaults to 5 seconds.
        :returns: A sequence of relative path strings for all descendants.
        """
        return [
            path for path, _node in self.enumerate_nodes(depth=depth, timeout=timeout)
        ]

    def enumerate_nodes(
        self,
        *,
        depth: int = 1,
        timeout: timedelta = timedelta(seconds=5),
    ) -> Sequence[tuple[str, AbstractTreeNode]]:
        """Enumerate descendant paths paired with their concrete node objects.

        Returns relative path strings from the current container for all descendant
        nodes, including both directories and pages, paired with the exact in-memory
        node instance each path came from.

        :param depth: The maximum depth to traverse. Default is 1 (only immediate children).
        :param timeout: The maximum time to spend enumerating children. Defaults to 5 seconds.
        :returns: A sequence of ``(relative_path, node)`` pairs for all descendants.
        """
        return self._enumerate_nodes(depth=depth, timeout=timeout)

    def enumerate_dirs(
        self,
        *,
        depth: int = 1,
        timeout: timedelta = timedelta(seconds=5),
    ) -> Sequence[str]:
        """Enumerate descendant directory paths.

        Returns relative path strings from the current container for all descendant
        directories (excluding pages). Each path is relative to this container.

        :param depth: The maximum depth to traverse. Default is 1 (only immediate children).
        :param timeout: The maximum time to spend enumerating children. Defaults to 5 seconds.
        :returns: A sequence of relative path strings for all descendant directories.
        """
        all_nodes = self.enumerate_nodes(depth=depth, timeout=timeout)
        return [path for path, node in all_nodes if node.is_dir()]

    def enumerate_pages(
        self,
        *,
        depth: int = 1,
        timeout: timedelta = timedelta(seconds=5),
    ) -> Sequence[str]:
        """Enumerate descendant page paths.

        Returns relative path strings from the current container for all descendant
        pages (excluding directories). Each path is relative to this container.

        :param depth: The maximum depth to traverse. Default is 1 (only immediate children).
        :param timeout: The maximum time to spend enumerating children. Defaults to 5 seconds.
        :returns: A sequence of relative path strings for all descendant pages.
        """
        all_nodes = self.enumerate_nodes(depth=depth, timeout=timeout)
        return [path for path, node in all_nodes if not node.is_dir()]

    def create(  # noqa: PLR0912
        self,
        cls: type[T],
        name: str | NotebookPath,
        *,
        parents: bool = False,
        if_exists: InsertBehavior = InsertBehavior.Raise,
    ) -> T:
        """Create a child page or directory in this container.

        :param cls: The class of the node to create (e.g., :class:`~labapi.tree.page.NotebookPage` or :class:`~labapi.tree.directory.NotebookDirectory`).
        :param name: The name of the new node.
        :param parents: If True, intermediate directories in the path will be created
                        using `InsertBehavior.Retain` if they don't exist.
        :param if_exists: The behavior to take if a node with the same name and
                          type already exists. Defaults to
                          ``InsertBehavior.Raise``.
        :returns: The newly created (or existing) node of type `cls`.
        :raises NodeExistsError: If ``if_exists`` is
                                 ``InsertBehavior.Raise`` and the node already
                                 exists.
        """
        normalized_name = (
            NotebookPath(EscapedSegment(name)) if isinstance(name, str) else name
        )
        path = normalized_name.resolve(self.path).relative_to(self)

        if len(path) == 0:
            raise ValueError("Path cannot be empty")
        if len(path) == 1:
            nodes = [n for n in self[Index.Name : path.name] if isinstance(n, cls)]

            if nodes:
                match if_exists:
                    case InsertBehavior.Raise:
                        raise NodeExistsError(
                            f'{cls.__name__} with name "{name}" already exists'
                        )
                    case InsertBehavior.Retain:
                        return nodes[0]
                    case InsertBehavior.Replace:
                        for node in nodes:
                            node.delete()

            create_tree = self.user.api_get(
                "tree_tools/insert_node",
                nbid=self.root.id,
                parent_tree_id=self.tree_id,
                display_text=path.name,
                is_folder=(
                    "true" if issubclass(cls, AbstractTreeContainer) else "false"
                ),
            )

            tree_id = extract_etree(create_tree, {"node": {"tree-id": str}})["tree-id"]

            new_node = cls(tree_id, path.name, self.root, self, self.user)
            if isinstance(new_node, AbstractTreeContainer):
                new_node._populated = True
            self._children.append(new_node)
            return new_node
        if parents:
            next_node = self.dir(*NotebookPath.escape(path[0]))

            return next_node.create(
                cls,
                path,
                parents=True,
                if_exists=if_exists,
            )

        raise ValueError(
            f'Parent path for "{name}" does not exist. Set `parents=True` to create it.'
        )

    def dir(self, name: str | NotebookPath) -> NotebookDirectory:
        """Ensure a directory exists at ``name`` and return it.

        Shorthand for :meth:`create` with ``cls=NotebookDirectory``,
        ``if_exists=InsertBehavior.Retain``, and ``parents=True``.

        :param name: The name or path of the directory.
        :returns: The ensured :class:`~labapi.tree.directory.NotebookDirectory`.
        """
        from .directory import NotebookDirectory

        return self.create(
            NotebookDirectory,
            name,
            parents=True,
            if_exists=InsertBehavior.Retain,
        )

    def page(self, name: str | NotebookPath) -> NotebookPage:
        """Ensure a page exists at ``name`` and return it.

        Shorthand for :meth:`create` with ``cls=NotebookPage``,
        ``if_exists=InsertBehavior.Retain``, and ``parents=True``.

        :param name: The name or path of the page.
        :returns: The ensured :class:`~labapi.tree.page.NotebookPage`.
        """
        from .page import NotebookPage

        return self.create(
            NotebookPage,
            name,
            parents=True,
            if_exists=InsertBehavior.Retain,
        )

    @override
    def is_dir(self) -> Literal[True]:
        """Return ``True`` because containers are directories.

        :returns: Always True.
        """
        return True

    @override
    def refresh(self) -> Self:
        """Refresh this container by clearing its cached children.

        This method clears the internal children cache, forcing the container
        to re-fetch its children from the LabArchives API on the next access.
        """
        # TODO if a child node is removed it won't know about it.
        for child in self._children:
            child.refresh()
        self._children = []
        self._populated = False

        return self
