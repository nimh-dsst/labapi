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
       |-- TraversalError
       |-- ExtractionError
       |   `-- TreeChildParseError
       `-- PartialEntryCreateError

``ExtractionError`` also inherits from :class:`ValueError`.

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
   Raises :class:`~labapi.exceptions.TraversalError` when a path segment is not
   found, or when an intermediate segment is not a directory.

Any call that sends a request to LabArchives
   Raises :class:`~labapi.exceptions.AuthenticationError` when LabArchives
   rejects the credentials or session, and
   :class:`~labapi.exceptions.ApiError` for any other non-2xx response. Both
   carry the LabArchives code in ``error_code``.

   Raises :class:`~labapi.exceptions.TransportError` when no HTTP response
   arrives: DNS, connect, TLS, proxy, or timeout failures, or a stream broken
   mid-read. It subclasses ``ApiError``, so ``except ApiError`` catches both.

Related Pages
-------------

- :ref:`paths` for traversal rules and parent-navigation behavior.
- :ref:`creating_pages` for duplicate-create behavior in practice.
- :ref:`limitations` for known limitations.
