.. _index_access:

Accessing Items with Index
==========================

Use ``Index`` to look up notebooks, directories, and pages by ID, or to get
every item with a given name.

.. warning::
   ``coll["name"]`` returns the first match when names are duplicated. Use
   ``coll[Index.Id: "..."]`` to select one item by ID.

Supported Collection Types
--------------------------

``Index``-based lookup is supported for:

- ``user.notebooks``
- Tree containers such as :class:`~labapi.tree.notebook.Notebook` and
  :class:`~labapi.tree.directory.NotebookDirectory`

.. warning::
   Page ``Entries`` do not support ``Index`` slicing. Access entries by
   integer index, iteration, or entry ID string.

.. note::
   Iterating over ``user.notebooks`` or a tree container yields names. Use
   ``values()`` for objects and ``items()`` for ``(name, object)`` pairs.

Basic Access by Name
--------------------

A string key looks up by name:

.. code-block:: python

   notebook = user.notebooks["My Research Notebook"]
   experiments = notebook["Experiments"]

To include duplicates, call ``all_keys()``, ``all_items()``,
or ``all_values()`` instead of ``keys()``, ``items()``, or ``values()``.

Explicit Indexing with ``Index``
--------------------------------

Slice with :class:`~labapi.util.types.Index` to look up by ID or by name.

Access by ID
~~~~~~~~~~~~

.. code-block:: python

   from labapi import Index

   notebook = user.notebooks[Index.Id:"12345"]
   page = notebook[Index.Id:"67890"]

Access by Name
~~~~~~~~~~~~~~

.. code-block:: python

   from labapi import Index

   shared_notebooks = user.notebooks[Index.Name:"Shared Data"]
   protocols = experiments[Index.Name:"Protocol"]

Summary of Indexing Methods
---------------------------

+---------------------------+---------------------------+----------------------------------------+
| Syntax                    | Method                    | Returns                                |
+===========================+===========================+========================================+
| ``coll["name"]``          | Implicit name lookup      | First item with matching name          |
+---------------------------+---------------------------+----------------------------------------+
| ``coll[Index.Id: "id"]``  | Explicit ID lookup        | The unique item with matching ID       |
+---------------------------+---------------------------+----------------------------------------+
| ``coll[Index.Name: "n"]`` | Explicit name list lookup | A list of all items with matching name |
+---------------------------+---------------------------+----------------------------------------+

Related Pages
-------------

- :ref:`paths` for path traversal and duplicate-name caveats.
- :ref:`limitations` for the broader capability summary.
- :ref:`integration_design` for advice on storing IDs in integrations.
