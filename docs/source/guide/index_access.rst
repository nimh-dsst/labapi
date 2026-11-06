.. _index_access:

Accessing Items with Index
==========================

Use ``Index`` when you want explicit, deterministic lookup behavior for
notebooks, directories, and pages.

.. warning::
   Name-based lookup is ambiguous when duplicate names exist.
   ``coll["name"]`` returns the first match and can silently select the wrong
   item. For deterministic access in integration code, use
   ``coll.get_by_id("...")``.

Supported Collection Types
--------------------------

``Index``-based lookup is supported for:

- ``user.notebooks``
- Tree containers such as :class:`~labapi.tree.notebook.Notebook` and
  :class:`~labapi.tree.directory.NotebookDirectory`

.. warning::
   Page ``Entries`` do not support ``Index`` slicing. Access entries by
   integer index, iteration, or ``entries.get_by_id("...")``; see
   :ref:`entries`.

.. note::
   Iterating over ``user.notebooks`` or a tree container yields names. Use
   ``values()`` for objects and ``items()`` for ``(name, object)`` pairs.

Basic Access by Name
--------------------

By default, a string key looks up the first item with that name:

.. code-block:: python

   notebook = user.notebooks["My Research Notebook"]
   experiments = notebook["Experiments"]

If you need duplicate-preserving results, call ``all_keys()``, ``all_items()``,
or ``all_values()`` instead of ``keys()``, ``items()``, or ``values()``.

Lookup by ID or Name
--------------------

``get_by_id()`` and ``get_by_name()`` are the recommended way to look items up
explicitly. They work on ``user.notebooks`` and on tree containers.

.. code-block:: python

   notebook = user.notebooks.get_by_id("12345")
   page = notebook.get_by_id("67890")

   shared_notebooks = user.notebooks.get_by_name("Shared Data")
   protocols = experiments.get_by_name("Protocol")

- ``get_by_id(id)`` returns the single item with that ID and raises
  :class:`KeyError` if there is none.
- ``get_by_name(name)`` returns a list of every item with that name. Names are
  not unique, so the list can hold several items, or none.

Default Notebook
~~~~~~~~~~~~~~~~

``user.notebooks.default`` is the notebook LabArchives marks as the user's
default, or ``None`` if none is marked:

.. code-block:: python

   notebook = user.notebooks.default
   if notebook is None:
       notebook = user.notebooks.get_by_name("My Research Notebook")[0]

Snapshot by ID: ``children_by_id``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A tree container's ``children_by_id`` property returns a ``dict`` from child
ID to child node. IDs are unique, so unlike name-keyed views no child is lost
when two share a name.

.. code-block:: python

   by_id = notebook.children_by_id
   for child_id, child in by_id.items():
       print(child_id, child.name)

The dict is a snapshot taken when you read the property. Changing it does not
change the container, and it does not pick up later changes such as
:meth:`~labapi.tree.mixins.AbstractTreeContainer.refresh` or newly created
children. Read the property again for a current view.

Explicit Indexing with ``Index``
--------------------------------

:class:`~labapi.util.types.Index` slicing does the same lookups as
``get_by_id()`` and ``get_by_name()`` and still works:

.. code-block:: python

   from labapi import Index

   notebook = user.notebooks[Index.Id:"12345"]            # same as get_by_id
   shared = user.notebooks[Index.Name:"Shared Data"]      # same as get_by_name

Summary of Lookup Methods
-------------------------

+------------------------------+---------------------------+----------------------------------------+
| Syntax                       | Method                    | Returns                                |
+==============================+===========================+========================================+
| ``coll["name"]``             | Implicit name lookup      | First item with matching name          |
+------------------------------+---------------------------+----------------------------------------+
| ``coll.get_by_id("id")``     | ID lookup                 | The unique item with matching ID       |
| ``coll[Index.Id: "id"]``     |                           | (``KeyError`` if none)                 |
+------------------------------+---------------------------+----------------------------------------+
| ``coll.get_by_name("n")``    | Name list lookup          | A list of all items with matching name |
| ``coll[Index.Name: "n"]``    |                           | (empty if none)                        |
+------------------------------+---------------------------+----------------------------------------+
| ``container.children_by_id`` | ID snapshot               | A ``dict`` of child ID to child node   |
+------------------------------+---------------------------+----------------------------------------+
| ``user.notebooks.default``   | Default notebook          | The default notebook, or ``None``      |
+------------------------------+---------------------------+----------------------------------------+

Related Pages
-------------

- :ref:`paths` for path traversal and duplicate-name caveats.
- :ref:`limitations` for the broader capability summary.
- :ref:`integration_design` for ID-first integration guidance.
