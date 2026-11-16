.. _delete:

Deleting Pages and Directories
==============================

:meth:`~labapi.tree.mixins.AbstractTreeNode.delete` renames a page or
directory with a deletion timestamp and moves it to the ``API Deleted Items``
folder under the notebook root. Nothing is permanently erased.

Delete a Page
-------------

.. code-block:: python

   page = notebook.traverse("My Folder/Page to Delete")
   page.delete()

After deletion, the page is renamed to something like:

.. code-block:: text

   Page to Delete - Deleted at 2024-01-15 14:30:22

Delete a Directory
------------------

.. code-block:: python

   directory = notebook.traverse("Old Project")
   directory.delete()

The directory's pages and subdirectories move with it.

Recover Deleted Items
---------------------

To recover a deleted item, navigate to ``API Deleted Items`` and move it back:

.. code-block:: python

   from labapi import Index

   deleted_items = notebook[Index.Name:"API Deleted Items"][0]
   deleted_page = deleted_items["Page to Delete - Deleted at 2024-01-15 14:30:22"]

   original_folder = notebook.traverse("My Folder")
   deleted_page.move_to(original_folder)
   deleted_page.name = "Page to Delete"

Entry Deletion
--------------

.. note::
   Entries cannot be deleted through the API.

Related Pages
-------------

- :ref:`entries` for which entry types can be read or updated.
- :ref:`limitations` for known API operations that ``labapi`` does not
  implement.
- :ref:`copying` for duplicating pages and directories.
