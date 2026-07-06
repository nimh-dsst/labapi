.. _architecture:

Contributor Architecture Guide
==============================

This guide documents the current internal architecture of ``labapi`` for
contributors working on tree, entry, and client internals.

The intent is to describe **current behavior and invariants**, including places
where the design is intentionally incomplete.

Subsystem Map
-------------

At a high level, runtime flow goes through these layers:

1. :class:`~labapi.client.Client`
2. :class:`~labapi.user.User`
3. Tree model (:class:`~labapi.tree.collection.Notebooks` ->
   :class:`~labapi.tree.notebook.Notebook` ->
   :class:`~labapi.tree.directory.NotebookDirectory` /
   :class:`~labapi.tree.page.NotebookPage`)
4. Entry model (:class:`~labapi.entry.collection.Entries` and
   :class:`~labapi.entry.entries.base.Entry` subclasses)
5. Utility layer (:mod:`labapi.util` helpers such as
   :class:`~labapi.util.path.NotebookPath`,
   indexing types, and XML extraction)

Client and User Boundary
~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~labapi.client.Client` is responsible for connection/auth concerns and
request signing. Its URL construction/signing helpers append the AKID, expiry,
and HMAC-SHA512 signature to requests.

:class:`~labapi.user.User` wraps an authenticated session and provides
:meth:`~labapi.user.User.api_get`/:meth:`~labapi.user.User.api_post` that always
add ``uid``. Most internal modules call the API through
:class:`~labapi.user.User` rather than directly through
:class:`~labapi.client.Client`.

Tree Model Boundary
~~~~~~~~~~~~~~~~~~~

The tree model is split between mapping-style collections and node/container
mixins:

* :class:`~labapi.tree.collection.Notebooks` tracks the user-visible notebook
  list.
* :class:`~labapi.tree.notebook.Notebook` is both the logical root and a
  container.
* :class:`~labapi.tree.directory.NotebookDirectory` is a container node.
* :class:`~labapi.tree.page.NotebookPage` is a leaf node with lazy-loaded
  entries.

Most operations that mutate the notebook hierarchy are implemented in
``tree/mixins.py`` and then reused by concrete node types.

Entry Model Boundary
~~~~~~~~~~~~~~~~~~~~

:attr:`~labapi.tree.page.NotebookPage.entries` lazily fetches page entries and
materializes them as :class:`~labapi.entry.entries.base.Entry` subclasses.

The :class:`~labapi.entry.collection.Entries` collection owns page-level entry
creation methods and appends newly created entries to local state after
successful API calls.

Utility Layer Boundary
~~~~~~~~~~~~~~~~~~~~~~

The ``labapi.util`` package provides primitives that are shared by tree,
entry, and client modules:

* :class:`~labapi.util.path.NotebookPath` path normalization/resolution
* typed index markers (``Index.Id``/``Index.Name``)
* XML extraction and conversion helpers
* constants such as known part types

Cache model and invariants
--------------------------

Container Population Cache (``_populated``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:class:`~labapi.tree.mixins.AbstractTreeContainer` lazily loads children on
first access:

* :attr:`~labapi.tree.mixins.AbstractTreeContainer.children` and mapping access
  call the internal ``_ensure_populated()`` helper.
* ``_ensure_populated()`` fetches
  ``tree_tools/get_tree_level`` once and marks the container as populated.
* :meth:`~labapi.tree.mixins.AbstractTreeContainer.refresh` clears
  ``_children`` and resets ``_populated=False``.

.. note::
   While ``_populated`` is true, read APIs for that container use local
   ``_children`` without another tree-level API call.

Page Entries Cache (``_entries``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:attr:`~labapi.tree.page.NotebookPage.entries` is also lazy:

* ``_entries is None`` means "not loaded yet".
* first access fetches from ``tree_tools/get_entries_for_page`` and stores an
  :class:`~labapi.entry.collection.Entries` object.
* :meth:`~labapi.tree.page.NotebookPage.refresh` resets ``_entries`` back to
  ``None``.

.. note::
   Repeated ``page.entries`` access returns the same
   :class:`~labapi.entry.collection.Entries` object until refresh.

Path Cache (``_has_path``)
~~~~~~~~~~~~~~~~~~~~~~~~~~

Every tree node memoizes its :class:`~labapi.util.path.NotebookPath`:

* first :attr:`~labapi.tree.mixins.AbstractBaseTreeNode.path` access computes
  and caches a :class:`~labapi.util.path.NotebookPath` for the node.
* rename and move operations clear the
  cached path for the current node and any loaded descendants.

.. note::
   Cached paths are stable until the node or one of its loaded ancestors is
   renamed or moved.

Path Stability and Traversal Expectations
-----------------------------------------

:class:`~labapi.util.path.NotebookPath` canonicalizes path-like input and
supports:

* absolute and relative forms
* composition with ``/``
* resolution with parent anchors
* relative conversion via
  :meth:`~labapi.util.path.NotebookPath.relative_to`

Tree traversal uses path resolution semantics from
:class:`~labapi.util.path.NotebookPath`.
:meth:`~labapi.tree.mixins.AbstractBaseTreeNode.traverse` resolves relative
paths against ``self.path`` and then walks segments from ``self.root``.

Enumeration helpers build on the same traversal model:

* :meth:`~labapi.tree.mixins.AbstractTreeContainer.enumerate_nodes` returns
  ``(relative_path, node)`` pairs for concrete descendant objects.
* :meth:`~labapi.tree.mixins.AbstractTreeContainer.enumerate_all`,
  :meth:`~labapi.tree.mixins.AbstractTreeContainer.enumerate_dirs`, and
  :meth:`~labapi.tree.mixins.AbstractTreeContainer.enumerate_pages` derive
  from that shared traversal so duplicate names do not get re-resolved through
  ``traverse()``.

Mutation Invariants and Refresh Expectations
--------------------------------------------

General Rule
~~~~~~~~~~~~

Mutating methods first call the API and then update local in-memory state when
the API call succeeds.

Create Operations
~~~~~~~~~~~~~~~~~

:meth:`~labapi.tree.mixins.AbstractTreeContainer.create` inserts new nodes and
appends them to ``self._children``. For container nodes, the new node starts
with ``_populated=True`` and empty children.

When ``if_exists=InsertBehavior.Replace``, existing matching nodes are deleted
before creating a replacement.

Move Operations
~~~~~~~~~~~~~~~

:meth:`~labapi.tree.mixins.AbstractTreeNode.move_to` updates the server parent,
then mutates both local parents:

* removes the node from old parent ``_children``
* switches ``_parent``
* appends to destination ``_children``
* invalidates cached paths for the moved node and any loaded descendants

Delete Operations
~~~~~~~~~~~~~~~~~

:meth:`~labapi.tree.mixins.AbstractTreeNode.delete` is implemented as
move-to-trash semantics:

* ensure/create an ``API Deleted Items`` directory under notebook root
* rename node to include deletion timestamp
* call :meth:`~labapi.tree.mixins.AbstractTreeNode.move_to` with the trash
  folder as destination

This means local state continues to reference the same Python object, but under
its new parent and new name.

When to Call Refresh
~~~~~~~~~~~~~~~~~~~~

Use :meth:`~labapi.tree.mixins.AbstractTreeContainer.refresh` (or
:meth:`~labapi.tree.page.NotebookPage.refresh` for page entries) before reading
changes made by another user, the web UI, or another API session, or when you
need to force a re-fetch.

Current behavior is intentionally shallow:

* container ``refresh()`` clears child caches, but pre-existing child objects
  held elsewhere are not automatically reconciled
* page ``refresh()`` clears the page's entries cache, but existing entry
  instances are not invalidated in place

Other Entry Types
-----------------


When page entries are loaded, unrecognized part types are wrapped as
:class:`~labapi.entry.entries.unknown.UnknownEntry` and
recognized-but-unimplemented types as
:class:`~labapi.entry.entries.unknown.UnimplementedEntry`, with warnings in
:attr:`~labapi.tree.page.NotebookPage.entries`.

Known Limitations and TODOs
---------------------------

* individual entry deletion is not implemented
* ``create_json_entry()`` creates an ``AttachmentEntry`` and a ``TextEntry``;
  no wrapper object represents the pair

Contributor Checklist for Internal Changes
------------------------------------------

Before changing tree/entry/client internals:

1. Identify which cache invariants your change touches (``_populated``,
   ``_entries``, ``_has_path``).
2. Decide whether in-memory objects must be mutated immediately or whether
   :meth:`~labapi.tree.mixins.AbstractTreeContainer.refresh` /
   :meth:`~labapi.tree.page.NotebookPage.refresh` should be required.
3. Ensure parent/child bookkeeping stays symmetric for moves/deletes.
4. If you add or change entry types, confirm
   entry registration plus
   :meth:`~labapi.entry.entries.base.Entry.from_part_type` dispatch behavior.
5. Update this page (and related guide pages) when module boundaries or
   invariants change.

Related Pages
-------------

* :ref:`contributing`
* :ref:`integration_design`
* :ref:`clearing_cache`
