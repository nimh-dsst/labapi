.. _navigating:

Navigating the Tree
===================

Once you have a :class:`~labapi.tree.notebook.Notebook` object, you can move
through its directories and pages in several ways. The examples below assume
you already have a ``notebook`` object from :ref:`first_calls`.

.. warning::
   Duplicate-name and first-match behavior are documented in
   :ref:`index_access`. Review that page before relying on name-based lookup in
   automation code.

Traversing the Tree with Paths
------------------------------

Use :meth:`~labapi.tree.mixins.AbstractBaseTreeNode.traverse`, which accepts a
slash-separated path string.

.. code-block:: python

   page = notebook.traverse("Experiments/Project A/Results")

   experiments = notebook.traverse("Experiments")
   project_a = experiments.traverse("Project A")

Fluent Navigation with ``dir()`` and ``page()``
-----------------------------------------------

To create or retrieve nodes while chaining calls, use
:meth:`~labapi.tree.mixins.AbstractTreeContainer.dir` and
:meth:`~labapi.tree.mixins.AbstractTreeContainer.page`.

These methods return the existing node if it is present, or create it if it is
missing.

.. code-block:: python

   page = notebook.dir("Experiments").dir("Project A").page("Results")
   page = notebook.dir("Experiments/Project A").page("Results")

See :meth:`~labapi.tree.mixins.AbstractTreeContainer.create` to set
duplicate-handling and parent-creation behavior.

Accessing Children by Name
--------------------------

Use dictionary-style indexing to get the first child with a matching name:

.. code-block:: python

   experiments = notebook["Experiments"]
   project_a = experiments["Project A"]

.. note::
   For deterministic lookup in integration code, prefer ID-based access with
   :attr:`~labapi.util.types.Index.Id`.

Accessing Children by ID or Name
--------------------------------

Use :class:`~labapi.util.types.Index` when you need to choose ID or name
lookup explicitly.

Access by ID
~~~~~~~~~~~~

.. code-block:: python

   from labapi import Index

   page = notebook[Index.Id:"123.45"]

Access by Name
~~~~~~~~~~~~~~

.. code-block:: python

   from labapi import Index

   results_pages = notebook[Index.Name:"Results"]

Enumerating Children
--------------------

``labapi`` provides enumeration helpers on
:class:`~labapi.tree.notebook.Notebook` and
:class:`~labapi.tree.directory.NotebookDirectory`.

List All Children
~~~~~~~~~~~~~~~~~

.. code-block:: python

   all_items = notebook.enumerate_all()
   all_items = notebook.enumerate_all(depth=3)

   experiments = notebook["Experiments"]
   experiment_items = experiments.enumerate_all(depth=2)

``depth`` limits how many levels of the tree are walked. Given this tree
structure::

   Notebook/
   |-- Experiments/
   |   |-- 2024/
   |   |   `-- Results
   |   `-- Archive
   `-- Notes

- ``depth=1`` returns ``["Experiments", "Notes"]``.
- ``depth=2`` returns
  ``["Experiments", "Experiments/2024", "Experiments/Archive", "Notes"]``.
- ``depth=3`` returns
  ``["Experiments", "Experiments/2024", "Experiments/2024/Results", "Experiments/Archive", "Notes"]``.

List Only Directories
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   directories = notebook.enumerate_dirs()
   directories = notebook.enumerate_dirs(depth=2)

   experiments = notebook["Experiments"]
   subdirs = experiments.enumerate_dirs()

List Only Pages
~~~~~~~~~~~~~~~

.. code-block:: python

   pages = notebook.enumerate_pages()
   pages = notebook.enumerate_pages(depth=2)

   experiments = notebook["Experiments"]
   experiment_pages = experiments.enumerate_pages(depth=2)

Accessing Parent and Root
-------------------------

Every node except the root has a
:attr:`~labapi.tree.mixins.AbstractBaseTreeNode.parent`. Any node can also
reach the notebook root through
:attr:`~labapi.tree.mixins.AbstractBaseTreeNode.root`.

.. code-block:: python

   page = notebook.traverse("Experiments/Project A/Results")
   project_a = page.parent
   notebook_root = page.root

Type-Safe Directory Access
--------------------------

Use :meth:`~labapi.tree.mixins.AbstractBaseTreeNode.as_dir` when you need to
tell a type checker that a node is a directory:

.. code-block:: python

   from labapi import NotebookPage

   node = notebook.traverse("Experiments/Project A")
   if node.is_dir():
       directory = node.as_dir()
       directory.create(NotebookPage, "New Page")

If you call :meth:`~labapi.tree.mixins.AbstractBaseTreeNode.as_dir` on a page,
it raises :class:`TypeError`.

Related Pages
-------------

- :ref:`first_calls` for getting the initial ``notebook`` object.
- :ref:`paths` for how paths are parsed and resolved.
- :ref:`index_access` for duplicate-name and explicit lookup behavior.
