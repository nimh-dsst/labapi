.. _limitations:

Capabilities and Limitations
============================

Current Capabilities
--------------------

``labapi`` supports:

* Navigating notebooks, directories, and pages by path or index.
* Searching notebook entries with paginated results.
* Creating and editing text entries (rich text, plain text, and headers).
* Uploading and updating attachment entries.
* Copying pages and directories for supported entry types.
* Creating notebooks and downloading native whole-notebook backups.
* Refreshing cached tree/page state when collaborating across sessions.

Known Limitations and Caveats
-----------------------------

Unsupported entry types are wrapped as fallback entries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a page contains entry types that ``labapi`` does not model yet, those
entries are loaded with a warning: unrecognized part types are wrapped as
:class:`~labapi.entry.entries.unknown.UnknownEntry`, and
recognized-but-unimplemented types as
:class:`~labapi.entry.entries.unknown.UnimplementedEntry`. The objects keep
their order and IDs, but assigning ``content`` raises ``NotImplementedError``.

Widget entries are read-only
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~labapi.entry.entries.widget.WidgetEntry` is supported for reading only.

Duplicate names return first-match results by default
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Name-based lookup methods such as ``collection["name"]`` and path traversal return the first match when duplicates exist.
Look up by ID to select one item, or use ``Index.Name`` to get every match.

Reserved ``".."`` path segments cannot be addressed by name
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Path traversal treats ``".."`` as parent navigation, so nodes literally named ``".."`` cannot be
resolved via :meth:`~labapi.tree.mixins.AbstractBaseTreeNode.traverse`.

``refresh()`` does not update old child references
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After ``refresh()``, child objects (entries, pages, directories) you fetched
earlier are stale. Fetch them again from the parent.

``copy_to()`` has copy fidelity limits and placement restrictions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* LabArchives may rename attachments during copy.
* Widget, unknown, and unimplemented entries may be skipped during page copy.
* When an entry cannot be recreated, ``copy_to()`` emits a ``RuntimeWarning`` and skips that
  entry; the copied page may be incomplete. Pass ``strict=True`` to abort the copy instead.
* When a copy fails, the page or directory it created is moved to *API Deleted Items*.
* Copying a directory into itself or into one of its descendants raises :class:`ValueError`.

``enumerate_all()`` can return partial results on larger trees
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``enumerate_all()`` stops after a time limit (about 5 seconds by default) and
returns the paths collected so far. On large or slow trees, use a smaller
``depth`` or enumerate one subtree at a time.

Entry deletion is not available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``labapi`` cannot delete individual entries, only pages and directories.

Comments are not available
~~~~~~~~~~~~~~~~~~~~~~~~~~

The :class:`~labapi.entry.comment.Comment` type is a placeholder. ``labapi``
cannot read or write entry comments.

Notebook creation has no matching deletion operation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:meth:`~labapi.tree.collection.Notebooks.create_notebook` creates an empty
notebook, but ``labapi`` cannot delete a notebook. A job that creates
notebooks leaves them behind.

Native backups operate on an entire notebook
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:meth:`~labapi.tree.notebook.Notebook.backup` downloads a native backup of the
whole notebook and cannot be limited to one directory or page. Excluding
attachments makes the download smaller. LabArchives restricts backups to the
notebook owner, so a user with shared access cannot download one.

Related Pages
-------------

* :ref:`entries`
* :ref:`index_access`
* :ref:`paths`
* :ref:`clearing_cache`
* :doc:`../quick_start/navigating`
* :doc:`../quick_start/copying`
* :doc:`../quick_start/deleting`
