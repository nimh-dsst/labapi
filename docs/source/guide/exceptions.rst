.. _exceptions:

Exception Types
===============

The public exception classes can be imported from ``labapi``.

Public Exception Hierarchy
--------------------------

All custom exceptions inherit from
:class:`~labapi.exceptions.LabArchivesError`:

.. code-block:: text

   Exception
   `-- LabArchivesError
       |-- AuthenticationError
       |-- ApiError
       |   `-- TransportError
       |-- NodeExistsError
       |-- PathError
       `-- TraversalError

``ExtractionError``, which also inherits from :class:`ValueError`, and its
subclass ``TreeChildParseError`` are not exported from ``labapi``; import them
from ``labapi.exceptions``.

For example:

.. code-block:: python

   from labapi import LabArchivesError, NodeExistsError, NotebookPage, TraversalError

   try:
       page = notebook.create(NotebookPage, "Experiments/2024/Results")
   except NodeExistsError:
       ...
   except ValueError:
       ...
   except TraversalError:
       ...
   except LabArchivesError:
       ...

Common Operations and Raised Exceptions
---------------------------------------

:meth:`~labapi.tree.mixins.AbstractTreeContainer.create`
   Raises :class:`~labapi.exceptions.NodeExistsError` when creating a duplicate
   node with
   ``if_exists=InsertBehavior.Raise``.

   Raises :class:`ValueError` for any multi-segment path when
   ``parents=False``, even if the intermediate directories exist.

:meth:`~labapi.tree.mixins.AbstractBaseTreeNode.traverse`
   Raises :class:`~labapi.exceptions.TraversalError` when an intermediate path
   segment exists but is not a directory.

Related Pages
-------------

- :ref:`paths` for traversal rules and parent-navigation behavior.
- :ref:`creating_pages` for duplicate-create behavior in practice.
- :ref:`limitations` for known limitations.
