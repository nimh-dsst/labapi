.. _limitations:

Capabilities and Limitations
============================

This page summarizes the current scope of ``labapi`` and its known limitations.

Current Capabilities
--------------------

``labapi`` supports these workflows reliably:

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
To avoid ambiguity, use ID-based lookup or explicit ``Index.Name`` access to retrieve all matches.

Reserved ``".."`` path segments cannot be addressed by name
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Path traversal treats ``".."`` as parent navigation, so nodes literally named ``".."`` cannot be
resolved via :meth:`~labapi.tree.mixins.AbstractBaseTreeNode.traverse`.

``refresh()`` does not update old child references
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After calling ``refresh()``, previously captured child objects (entries/pages/directories) still hold stale cached state.
Re-fetch children from the refreshed parent object instead of reusing old references.

``copy_to()`` has copy fidelity limits and placement restrictions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* LabArchives may rename attachments during copy.
* Widget, unknown, and unimplemented entries may be skipped during page copy.
* When an entry cannot be recreated, ``copy_to()`` emits a ``RuntimeWarning`` and skips that
  entry; the copied page may be incomplete.
* Copying a directory into itself or into one of its descendants raises :class:`ValueError`.

``enumerate_all()`` can return partial results on larger trees
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tree enumeration tracks elapsed wall-clock time (default: about 5 seconds) while traversing children.
When the elapsed-time limit is reached, traversal stops and returns the paths collected so far.
Treat ``enumerate_all()`` results as potentially truncated for very large or slow trees, and prefer smaller
``depth`` values and/or subtree-by-subtree enumeration when completeness matters.

Entry deletion is not available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Deleting individual entries (text, headers, attachments, widgets) is not currently supported by the API client.
Only page and directory deletion/move-to-trash workflows are available.

Comments are not available
~~~~~~~~~~~~~~~~~~~~~~~~~~

``labapi`` exposes a placeholder :class:`~labapi.entry.comment.Comment` type,
but it does not currently provide operations for reading, creating, updating,
or deleting entry comments.

Notebook creation has no matching deletion operation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:meth:`~labapi.tree.collection.Notebooks.create_notebook` creates an empty
notebook, but ``labapi`` cannot delete a notebook. Automated jobs that create
notebooks must therefore account for the persistent resources they leave
behind.

Native backups operate on an entire notebook
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:meth:`~labapi.tree.notebook.Notebook.backup` downloads a native backup of the
whole notebook; it cannot limit the request to one directory or page. Excluding
attachment payloads can reduce the download size, but the backup still covers
the entire notebook. LabArchives also restricts this operation to the notebook
owner, so a user with shared access may be able to navigate the notebook but
not download its native backup.

Planning Guidance
-----------------

For production integrations:

- Prefer ID-based addressing in automation.
- Refresh parent nodes before reads that must include external changes and then
  re-fetch child objects.
- Validate copied content, especially attachments and specialized entries.
- Add explicit handlers for unsupported entry types.
- Reuse a designated notebook for recurring automation unless permanent
  notebook creation is intentional.
- Plan whole-notebook backup storage and authenticate as the notebook owner.

Related Pages
-------------

* :ref:`entries`
* :ref:`index_access`
* :ref:`paths`
* :ref:`clearing_cache`
* :doc:`../quick_start/navigating`
* :doc:`../quick_start/copying`
* :doc:`../quick_start/deleting`
