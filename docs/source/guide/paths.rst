.. _paths:

Working with Paths
==================

Paths provide a way to navigate, reference, and create nodes in the notebook tree using Unix-style
slash-separated strings. This is an alternative to chained index access and is especially useful
when working with deeply nested structures.

.. warning::
   For duplicate-name and first-match lookup behavior, see
   :ref:`index_access`. This page focuses on path syntax and traversal rules.

.. code-block:: python

    from labapi import TraversalError

    # Index access (chained)
    page = notebook["Experiments"]["2024"]["Results"]

    # Path-based (equivalent)
    page = notebook.traverse("Experiments/2024/Results")

    try:
        notebook.traverse("Experiments/2024/Results/Figure 1")
    except TraversalError:
        # An intermediate segment exists but is not a directory
        ...

Traversing the Tree
-------------------

The :meth:`~labapi.tree.mixins.AbstractBaseTreeNode.traverse` method is available on any tree node
and accepts a slash-separated path string.

.. code-block:: python

    folder = notebook.traverse("Experiments")
    page = notebook.traverse("Experiments/2024/Results")

.. note::
   If duplicate sibling names appear in a path segment, ``traverse()``
   selects the first match for that segment. For deterministic selection,
   index from the parent container with ``Index.Id`` (see :ref:`index_access`).

Absolute vs Relative Paths
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Paths starting with ``/`` are **absolute** - they are resolved from the notebook root regardless
of where you call ``traverse``.

.. code-block:: python

    # Relative: resolved from `folder`
    page = folder.traverse("2024/Results")

    # Absolute: always resolved from the notebook root
    page = folder.traverse("/Experiments/2024/Results")

Parent Navigation
~~~~~~~~~~~~~~~~~

Use ``..`` to navigate to the parent container.

.. code-block:: python

    parent = page.traverse("..")
    grandparent = page.traverse("../..")

Escaping Path Separators
~~~~~~~~~~~~~~~~~~~~~~~~

Use a backslash to keep ``/`` as part of a path segment instead of treating it
as a separator.

.. code-block:: python

    figure = notebook.traverse(r"Experiments/Figure\/1")
    page = notebook.page(r"Reports\/2024")

.. note::
   To inspect duplicate child names under a container, use explicit indexing
   on that container (for example, ``container[Index.Name: "Results"]``)
   to retrieve all matches; then use ``Index.Id`` to select exactly one
   (see :ref:`index_access`).

.. warning::
   Nodes with the literal name ``".."`` cannot be accessed via ``traverse``,
   as ``..`` is reserved for parent navigation.

Enumerating Descendants
-----------------------

The enumeration methods return relative path strings for all descendants, up to a specified depth.
This is useful for listing or searching the tree without fetching every node individually.

.. code-block:: python

    # All descendants (directories and pages), depth 1 (default)
    notebook.enumerate_all()
    # e.g. ["Experiments", "Experiments/2024", "Protocols"]

    # Only directories
    notebook.enumerate_dirs(depth=2)

    # Only pages
    notebook.enumerate_pages(depth=2)

``depth`` defaults to ``1`` (immediate children only). To fetch the full tree you can increase
it, but be aware that this makes one API request per directory level visited.

.. code-block:: python

    # Enumerate up to 3 levels deep
    all_paths = notebook.enumerate_all(depth=3)

    for path in all_paths:
        node = notebook.traverse(path)
        print(path, "->", node.id)

Creating Nodes with Paths
-------------------------

The :meth:`~labapi.tree.mixins.AbstractTreeContainer.create` method accepts a path string (or
:class:`~labapi.util.path.NotebookPath`) as the ``name`` argument. When a multi-segment path is
provided, you must pass ``parents=True`` to allow intermediate directories to be created
automatically.

.. code-block:: python

    from labapi import NotebookPage, NotebookDirectory

    # Create a page at a nested path; intermediate directories are created as needed
    page = notebook.create(NotebookPage, "Experiments/2024/Results", parents=True)

    # Without parents=True, a ValueError is raised if an intermediate directory is missing
    page = notebook.create(NotebookPage, "Experiments/2024/Results")  # raises if missing

See :ref:`creating_pages` for details on the ``if_exists`` parameter and other creation options.

Convenience Methods: ``dir()`` and ``page()``
----------------------------------------------

For common "ensure this path exists" workflows, use the convenience methods
:meth:`~labapi.tree.mixins.AbstractTreeContainer.dir` and
:meth:`~labapi.tree.mixins.AbstractTreeContainer.page`.

These methods are shorthand for :meth:`~labapi.tree.mixins.AbstractTreeContainer.create`
with:

* ``parents=True`` (create missing intermediate directories), and
* ``if_exists=InsertBehavior.Retain`` (return an existing matching node instead of raising).

.. code-block:: python

    from labapi import NotebookDirectory, NotebookPage, InsertBehavior

    # Equivalent calls:
    reports_dir = notebook.dir("Experiments/2024/Reports")
    reports_dir = notebook.create(
        NotebookDirectory,
        "Experiments/2024/Reports",
        parents=True,
        if_exists=InsertBehavior.Retain,
    )

    summary_page = notebook.page("Experiments/2024/Summary")
    summary_page = notebook.create(
        NotebookPage,
        "Experiments/2024/Summary",
        parents=True,
        if_exists=InsertBehavior.Retain,
    )

When to Use Them
~~~~~~~~~~~~~~~~

Use ``dir()`` and ``page()`` when you want concise, idempotent setup code.
They are especially useful in scripts that may run repeatedly.

.. code-block:: python

    # Safe to run multiple times; existing nodes are returned.
    notebook.dir("Experiments/2024").page("Results")
    notebook.page("Experiments/2024/Raw Data")

Because both methods retain existing nodes, calling them again for the same
path returns the existing directory/page instead of creating a duplicate.

They can also be used for navigation when you expect the path to already
exist: the same call either returns the existing node or creates it if
missing.

.. code-block:: python

    # Navigate to an existing directory (or create it if needed)
    reports = notebook.dir("Experiments/2024/Reports")

    # Navigate to an existing page (or create it if needed)
    summary = notebook.page("Experiments/2024/Summary")

The NotebookPath Class
----------------------

:class:`~labapi.util.path.NotebookPath` is a structured path object that can be constructed from
nodes or strings, combined with ``/``, and converted back to strings. It is used internally by
``traverse`` and ``create``, but is also available for your own path logic.

**Constructing a path from a node:**

.. code-block:: python

    from labapi import NotebookPath

    path = NotebookPath(folder)
    print(path)           # /Experiments/2024
    print(path.name)      # 2024  (last segment)
    print(path.parts)     # ['Experiments']  (all but last)
    print(path.is_absolute())  # True

**Constructing from a string:**

.. code-block:: python

    abs_path = NotebookPath("/Experiments/2024")
    rel_path = NotebookPath("2024/Results")

**Combining paths with ``/``:**

.. code-block:: python

    base = NotebookPath(notebook)          # /
    path = base / "Experiments" / "2024"  # /Experiments/2024

**Resolving relative paths:**

.. code-block:: python

    rel = NotebookPath("Results")
    abs_path = rel.resolve(NotebookPath(folder))  # /Experiments/2024/Results

**Getting a relative path between two nodes:**

.. code-block:: python

    page_path = NotebookPath(page)                  # /Experiments/2024/Results
    rel = page_path.relative_to(folder)             # Results  (relative to /Experiments/2024)

**Checking containment:**

.. code-block:: python

    page_path.is_relative_to(folder)   # True if page is inside folder
    page_path.is_relative_to(notebook) # True (everything is inside the notebook)

Related Pages
-------------

* :ref:`index_access` for explicit lookup and duplicate-name behavior.
* :ref:`creating_pages` for path-based creation examples.
* :ref:`limitations` for current traversal and enumeration caveats.
