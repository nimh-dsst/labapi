.. _limitations:

Capabilities and Limitations
============================

This page summarizes the current scope of ``labapi`` and its known limitations.

Current Capabilities
--------------------

``labapi`` supports these workflows reliably:

* Navigating notebooks, directories, and pages by path or index.
* Creating and editing text entries (rich text, plain text, and headers).
* Uploading and updating attachment entries.
* Copying pages and directories for supported entry types.
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

Attachment update API can return a ``4999`` error
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some attachment update operations can fail with a LabArchives ``4999`` error response.
When this occurs during ``AttachmentEntry.content`` assignment, ``labapi`` raises
an :class:`~labapi.exceptions.ApiError` that includes the entry ID, filename, raw
LabArchives error, and recovery guidance. The original raw API failure remains
available as the exception cause.

Recommended recovery workflow:

1. Reload the page or re-fetch the attachment entry so local metadata matches the server.
2. Revalidate the filename, caption, MIME type, and backing stream before retrying.
3. Retry with a fresh :class:`~labapi.entry.attachment.Attachment` object or a fresh session.

Planning Guidance
-----------------

For production integrations:

- Prefer ID-based addressing in automation.
- Refresh parent nodes before reads that must include external changes and then
  re-fetch child objects.
- Validate copied content, especially attachments and specialized entries.
- Add explicit handlers for unsupported entry types and ``ApiError`` code
  ``4999`` during attachment updates.

Related Pages
-------------

* :ref:`entries`
* :ref:`index_access`
* :ref:`paths`
* :ref:`clearing_cache`
* :doc:`../quick_start/navigating`
* :doc:`../quick_start/copying`
* :doc:`../quick_start/deleting`
