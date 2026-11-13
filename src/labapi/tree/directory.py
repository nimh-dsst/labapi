"""Notebook Directory Module.

This module defines the :class:`~labapi.tree.directory.NotebookDirectory` class,
representing a directory (folder) within a LabArchives notebook. It extends
both :class:`~labapi.tree.mixins.AbstractTreeContainer` and
:class:`~labapi.tree.mixins.AbstractTreeNode` to allow it to contain other
nodes and be managed as a node itself.
"""

from __future__ import annotations

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
    def copy_to(
        self, destination: AbstractTreeContainer, *, strict: bool = False
    ) -> NotebookDirectory:
        """Copy this directory and its contents into ``destination``.

        This operation recursively copies all child directories and pages.
        Per-entry failures inside copied pages are handled as described in
        :meth:`NotebookPage.copy_to <labapi.tree.page.NotebookPage.copy_to>`.

        Failure handling: if the copy aborts (a descendant fails to copy, or, with
        ``strict=True``, any entry fails), the directory created here is moved to
        *API Deleted Items* before the error is re-raised (the public API has no
        hard delete), taking every descendant already copied into it along, so
        the destination no longer contains the partial copy.

        :param destination: The target container to copy the directory to.
        :param strict: If ``True``, any entry that fails to copy aborts the whole
            copy (and triggers the rollback above) instead of being warned about
            and skipped.
        :returns: A new instance of the copied directory in the destination.
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
                child.copy_to(new_dir, strict=strict)
        except Exception:
            new_dir.delete()
            raise

        return new_dir

    @property
    @override
    def id(self) -> str:
        """Return the directory identifier.

        :returns: The directory's ID.
        """
        return super().id
