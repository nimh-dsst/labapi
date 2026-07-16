.. _exceptions:

Exception Types
===============

``labapi`` exports its public exception classes at the package top level so
callers can reliably catch failures by category.

Public Exception Hierarchy
--------------------------

All custom exceptions inherit from
:class:`~labapi.exceptions.LabArchivesError`:

.. code-block:: text

   Exception
   `-- LabArchivesError
       |-- AuthenticationError
       |-- ApiError
       |-- NodeExistsError
       |-- PathError
       `-- TraversalError

``ExtractionError`` (which also inherits from :class:`ValueError`) and its
subclass ``TreeChildParseError`` also exist but are not exported at the
package top level; import them from ``labapi.exceptions``.

Import and catch these from ``labapi``:

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
- :ref:`limitations` for limitations not represented as exception types.
