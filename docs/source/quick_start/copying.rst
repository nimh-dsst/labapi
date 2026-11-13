.. _copying:

Copying Pages and Directories
=============================

Use :meth:`~labapi.tree.mixins.AbstractTreeNode.copy_to` to duplicate pages and
directories within or across notebooks.

Copy a Page
-----------

.. code-block:: python

   source_page = notebook.traverse("Experiments/Trial 1")
   destination = notebook.traverse("Archive")
   copied_page = source_page.copy_to(destination)

The copy has the same name. Entries that ``copy_to()`` cannot copy are skipped.

Copy Across Notebooks
---------------------

.. code-block:: python

   source_page = notebook1.traverse("Results/Final Results")
   destination = notebook2.traverse("Imported Data")
   copied_page = source_page.copy_to(destination)

Copy a Directory
----------------

Directories are copied with all their pages and subdirectories:

.. code-block:: python

   source_dir = notebook.traverse("2024 Experiments")
   destination = notebook.traverse("Archives")
   copied_dir = source_dir.copy_to(destination)

Return Value
------------

.. code-block:: python

   new_page = source_page.copy_to(destination)

   print(f"Original: {source_page.id}")
   print(f"Copy: {new_page.id}")

Limitations
-----------

.. warning::
   LabArchives can rename attachment files when copying. The file contents are
   unchanged.

.. warning::
   Only text, plain-text, header, and attachment entries are fully supported.
   Other entry types, including widgets, may be skipped after a
   ``RuntimeWarning``.

Pass ``strict=True`` to raise the entry's error instead of skipping it:

.. code-block:: python

   copied_page = source_page.copy_to(destination, strict=True)

If a copy fails, the page or directory it created is moved to
``API Deleted Items`` before the error is raised.

Best Practices
--------------

After copying, compare the entry counts and check the copied attachments'
filenames and contents:

.. code-block:: python

   original_page = notebook.traverse("Source/Page")
   copied_page = original_page.copy_to(notebook.traverse("Destination"))

   print(f"Original entries: {len(original_page.entries)}")
   print(f"Copied entries: {len(copied_page.entries)}")

Alternatives
------------

Move Instead of Copying
~~~~~~~~~~~~~~~~~~~~~~~

:meth:`~labapi.tree.mixins.AbstractTreeNode.move_to` moves a node within the
same notebook:

.. code-block:: python

   page.move_to(new_location)

Recreate Content Programmatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To control exactly what is copied, create a new page and add the entries
yourself:

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
