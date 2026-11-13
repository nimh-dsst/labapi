.. _paths:

Working with Paths
==================

A slash-separated path string names a node in the notebook tree, so you can reach or create a
deeply nested node in one call.

.. seealso::
   :ref:`index_access` for duplicate-name and first-match lookup behavior.

Web URLs
--------

Notebook and page ``url`` properties return direct LabArchives Web UI links.
They are not Share URLs: only signed-in users authorized to access the target
can view it.
For a custom API host, pass its Web UI base URL explicitly to
``Client(..., web_url="https://notebooks.example.com")``.

.. code-block:: python

    print(notebook.url)
    print(page.url)

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
   When siblings share a name, ``traverse()`` takes the first match.
   ``container[Index.Name: "Results"]`` lists all of them, and ``Index.Id``
   selects one (see :ref:`index_access`).

Absolute vs Relative Paths
~~~~~~~~~~~~~~~~~~~~~~~~~~~

A path starting with ``/`` is absolute: it is resolved from the notebook root, whichever node
you call ``traverse`` on.

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

Put a backslash before a ``/`` that belongs to a name. Every method that takes
a path string accepts this, including ``traverse()``, ``create()``, ``dir()``,
and ``page()``.

.. code-block:: python

    # Literal name "Figure/1"
    figure = notebook.traverse(r"Experiments/Figure\/1")

    # Literal name "Reports/2024"
    page = notebook.page(r"Reports\/2024")

Programmatic Escaping
^^^^^^^^^^^^^^^^^^^^^

If you are building paths from variables that might contain slashes, use
:meth:`~labapi.util.path.NotebookPath.escape` to escape the segments:

.. code-block:: python

    from labapi import NotebookPath

    raw_name = "Results / Final"
    # Escapes / and \ to prevent accidental traversal
    safe_name = NotebookPath.escape(raw_name)[0]

    # Now safe to use in a path string
    page = notebook.page(f"Experiments/{safe_name}")

Use :meth:`~labapi.util.path.NotebookPath.unescape` to remove escapes from a
segment string:

.. code-block:: python

    print(NotebookPath.unescape(r"Results\/Final")) # "Results/Final"

.. warning::
   Nodes with the literal name ``".."`` cannot be accessed via ``traverse``,
   as ``..`` is reserved for parent navigation.

Enumerating Descendants
-----------------------

The enumeration methods return the relative paths of descendants down to a given depth.

.. code-block:: python

    # All descendants (directories and pages) through depth 2
    notebook.enumerate_all(depth=2)
    # e.g. ["Experiments", "Experiments/2024", "Protocols"]

    # Only directories
    notebook.enumerate_dirs(depth=2)

    # Only pages
    notebook.enumerate_pages(depth=2)

``depth`` defaults to ``1``, the immediate children. Each directory visited costs one API
request.

.. code-block:: python

    # Enumerate up to 3 levels deep
    all_paths = notebook.enumerate_all(depth=3)

    for path in all_paths:
        node = notebook.traverse(path)
        print(path, "->", node.id)

.. note::
   Use :meth:`~labapi.tree.mixins.AbstractTreeContainer.enumerate_nodes` to get
   ``(path, node)`` pairs directly instead of re-traversing, since first-match
   name lookup can pick the wrong node when sibling names repeat.

Creating Nodes with Paths
-------------------------

The :meth:`~labapi.tree.mixins.AbstractTreeContainer.create` method accepts a path string (or
:class:`~labapi.util.path.NotebookPath`) as the ``name`` argument. A path with more than one
segment requires ``parents=True``, which creates any missing intermediate directories.

.. code-block:: python

    from labapi import NotebookPage, NotebookDirectory

    # Create a page at a nested path; intermediate directories are created as needed
    page = notebook.create(NotebookPage, "Experiments/2024/Results", parents=True)

    # Without parents=True, create() raises ValueError for any multi-segment path,
    # even when the intermediate directories already exist
    page = notebook.create(NotebookPage, "Experiments/2024/Results")  # raises ValueError

See :ref:`creating_pages` for details on the ``if_exists`` parameter and other creation options.

Convenience Methods: ``dir()`` and ``page()``
----------------------------------------------

:meth:`~labapi.tree.mixins.AbstractTreeContainer.dir` and
:meth:`~labapi.tree.mixins.AbstractTreeContainer.page` return the directory or
page at a path, creating it and any missing parents first if needed.

They are shorthand for :meth:`~labapi.tree.mixins.AbstractTreeContainer.create`
with ``parents=True`` and ``if_exists=InsertBehavior.Retain``, which returns an
existing matching node where ``create`` would otherwise raise.

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

.. code-block:: python

    # Safe to run multiple times; existing nodes are returned.
    notebook.dir("Experiments/2024").page("Results")
    notebook.page("Experiments/2024/Raw Data")

To navigate without creating anything, use ``traverse()``.

.. code-block:: python

    # Navigate to an existing directory (or create it if needed)
    reports = notebook.dir("Experiments/2024/Reports")

    # Navigate to an existing page (or create it if needed)
    summary = notebook.page("Experiments/2024/Summary")

The NotebookPath Class
----------------------

:class:`~labapi.util.path.NotebookPath` represents parsed notebook paths. Use it to compose,
resolve, compare, or stringify paths before calling ``traverse()`` or ``create()``.

**Constructing a path from a node:**

.. code-block:: python

    from labapi import NotebookPath

    path = NotebookPath(folder)
    print(path)           # /Experiments/2024
    print(path.name)      # 2024  (last segment)
    print(path.parts)     # ('Experiments',)  (all but last)
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
