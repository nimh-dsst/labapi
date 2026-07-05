.. _delete:

Deleting Pages and Directories
==============================

Use :meth:`~labapi.tree.mixins.AbstractTreeNode.delete` to move pages and
directories into the notebook's ``API Deleted Items`` folder. ``delete()``
renames the item and moves it to ``API Deleted Items``; it does not
permanently erase the item.

How Deletion Works
------------------

When you delete a page or directory:

1. The item is renamed with a deletion timestamp.
2. The item is moved to ``API Deleted Items`` under the notebook root.

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

Deleting a directory moves the directory itself — including all of its pages
and subdirectories — into ``API Deleted Items``.

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
   Individual entries such as text entries, attachments, and headers cannot be
   deleted through the API.

Related Pages
-------------

- :ref:`entries` for which entry types can be read or updated.
- :ref:`limitations` for known API operations that ``labapi`` does not
  implement.
- :ref:`copying` if you want duplication rather than moving content to
  ``API Deleted Items``.
