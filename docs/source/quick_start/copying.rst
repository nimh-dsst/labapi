.. _copying:

Copying Pages and Directories
=============================

Use :meth:`~labapi.tree.mixins.AbstractTreeNode.copy_to` to duplicate pages and
directories within or across notebooks. The examples assume you already have
the source node and destination container.

Copy a Page
-----------

.. code-block:: python

   source_page = notebook.traverse("Experiments/Trial 1")
   destination = notebook.traverse("Archive")
   copied_page = source_page.copy_to(destination)

This creates a new page in the destination directory with the same name and
its supported entries.

Copy Across Notebooks
---------------------

.. code-block:: python

   source_page = notebook1.traverse("Results/Final Results")
   destination = notebook2.traverse("Imported Data")
   copied_page = source_page.copy_to(destination)

Copy a Directory
----------------

Directories are copied recursively, including their pages and subdirectories:

.. code-block:: python

   source_dir = notebook.traverse("2024 Experiments")
   destination = notebook.traverse("Archives")
   copied_dir = source_dir.copy_to(destination)

Return Value
------------

``copy_to()`` returns the newly created copy:

.. code-block:: python

   new_page = source_page.copy_to(destination)

   print(f"Original: {source_page.id}")
   print(f"Copy: {new_page.id}")

Limitations
-----------

.. warning::
   LabArchives can rename attachment files during copy operations. The file
   data is preserved, but the copied filename may differ from the original.

.. warning::
   Only text, plain-text, header, and attachment entries are fully supported.
   Other entry types, including widgets, may be skipped after a
   ``RuntimeWarning``.

Best Practices
--------------

- Test copying with a disposable page or directory first.
- Verify the copied entry count, then open representative copied attachments
  and compare filenames and content.
- If filenames matter, re-read copied attachments and confirm their names.

Example verification:

.. code-block:: python

   original_page = notebook.traverse("Source/Page")
   copied_page = original_page.copy_to(notebook.traverse("Destination"))

   print(f"Original entries: {len(original_page.entries)}")
   print(f"Copied entries: {len(copied_page.entries)}")

Alternatives
------------

Move Instead of Copying
~~~~~~~~~~~~~~~~~~~~~~~

If you want to relocate content instead of duplicating it, use
:meth:`~labapi.tree.mixins.AbstractTreeNode.move_to` (moves are only possible
within the same notebook):

.. code-block:: python

   page.move_to(new_location)

Recreate Content Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When copy fidelity matters, create a new page and recreate only the entry
types you need:

.. code-block:: python

   from labapi import NotebookPage

   new_page = destination.create(NotebookPage, "New Page")

   for entry in original_page.entries:
       if entry.content_type == "text entry":
           new_page.entries.create(entry.__class__, entry.content)

Related Pages
-------------

- :ref:`limitations` for known copy limitations.
- :ref:`delete` for moving pages and directories to ``API Deleted Items``.
- :ref:`navigating` for finding source and destination locations.
