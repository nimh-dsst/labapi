"""Notebook Directory Module.

This module defines the :class:`~labapi.tree.directory.NotebookDirectory` class,
representing a directory (folder) within a LabArchives notebook. It extends
both :class:`~labapi.tree.mixins.AbstractTreeContainer` and
:class:`~labapi.tree.mixins.AbstractTreeNode` to allow it to contain other
nodes and be managed as a node itself.
"""

from __future__ import annotations

import warnings

from typing_extensions import override

from labapi.util import InsertBehavior

from .mixins import AbstractTreeContainer, AbstractTreeNode


class NotebookDirectory(AbstractTreeContainer, AbstractTreeNode):
    """Represents a directory (folder) within a LabArchives notebook.

    A `NotebookDirectory` can contain other directories and pages, forming
    a hierarchical structure. It inherits functionalities for both being a
    container and being a movable/modifiable node within the tree.
    """

    @override
    def copy_to(self, destination: AbstractTreeContainer) -> NotebookDirectory:
        """Copy this directory and its contents into ``destination``.

        This operation recursively copies all child directories and pages.

        Failure invariant: if copying any descendant aborts, the directory created
        here is rolled back before the error is re-raised. Deleting it cascades to
        every descendant already copied into it, so a failed recursive copy never
        leaves a partially created destination subtree behind.

        :param destination: The target container to copy the directory to.
        :returns: A new instance of the copied directory in the destination.
        :raises RuntimeWarning: Emitted when best-effort rollback of an aborted
            copy fails.
        """
        if self.is_parent_of(destination) or self is destination:
            raise ValueError(
                "Cannot copy a directory into itself or one of its descendants"
            )

        new_dir = destination.create(
            NotebookDirectory, self.name, if_exists=InsertBehavior.Ignore
        )

        try:
            for child in self.children:
                child.copy_to(new_dir)
        # Broad by design: any failure copying a descendant aborts the copy, so roll
        # back the whole subtree created here (deleting new_dir cascades) before
        # re-raising. A failed rollback must not mask the original error.
        except Exception:
            try:
                new_dir.delete()
            except Exception as cleanup_exc:  # noqa: BLE001
                warnings.warn(
                    f"Failed to roll back partially copied directory {new_dir.id!r} after "
                    f"a copy failure: {cleanup_exc}. The destination may contain a partial subtree.",
                    RuntimeWarning,
                    stacklevel=2,
                )
            raise

        return new_dir

    @property
    @override
    def id(self) -> str:
        """Return the directory identifier.

        :returns: The directory's ID.
        """
        return super().id
