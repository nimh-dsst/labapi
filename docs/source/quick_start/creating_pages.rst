.. _creating_pages:

Creating Pages and Entries
==========================

This page covers how to create directories and pages, then add entries to a
page. The examples assume you already have a ``notebook`` object from
:ref:`first_calls`.

Notebook Structure
------------------

LabArchives organizes content hierarchically:

- **Notebooks** contain directories and pages.
- **Directories** contain other directories and pages.
- **Pages** contain entries arranged from top to bottom.

Create Directories and Pages
----------------------------

Use :meth:`~labapi.tree.mixins.AbstractTreeContainer.create` to add new
:class:`NotebookDirectories <labapi.tree.directory.NotebookDirectory>` or
:class:`NotebookPages <labapi.tree.page.NotebookPage>`.

.. code-block:: python

   from labapi import NotebookDirectory, NotebookPage

   my_folder = notebook.create(NotebookDirectory, "Experiments")
   experiment_page = my_folder.create(NotebookPage, "Experiment 1")
   subfolder = my_folder.create(NotebookDirectory, "2024 Results")

.. note::
   Tree mutation methods update local cached objects immediately.

Handle Existing Nodes
~~~~~~~~~~~~~~~~~~~~~

By default, ``create()`` raises
:class:`~labapi.exceptions.NodeExistsError` if a node with the same name and
type already exists. Use ``if_exists`` to choose a different behavior:

.. code-block:: python

   from labapi import InsertBehavior, NotebookPage

   page = notebook.create(NotebookPage, "Existing Page", if_exists=InsertBehavior.Raise)
   page = notebook.create(NotebookPage, "Existing Page", if_exists=InsertBehavior.Ignore)
   page = notebook.create(NotebookPage, "Existing Page", if_exists=InsertBehavior.Retain)
   page = notebook.create(NotebookPage, "Existing Page", if_exists=InsertBehavior.Replace)

Create Entries
--------------

Use :meth:`~labapi.entry.collection.Entries.create` to add entries to a
page:

.. code-block:: python

   from labapi import Attachment, AttachmentEntry, HeaderEntry, PlainTextEntry, TextEntry

   page.entries.create(HeaderEntry, "Experiment Results")
   page.entries.create(TextEntry, "<p>This is <b>bold</b> text.</p>")
   page.entries.create(PlainTextEntry, "Simple unformatted text")
   page.entries.create(AttachmentEntry, Attachment.from_file("results.csv"))

Entry Types
~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 20 50

   * - Entry Class
     - Data Type
     - Description
   * - :class:`~labapi.entry.entries.text.HeaderEntry`
     - ``str``
     - Section headers and titles.
   * - :class:`~labapi.entry.entries.text.TextEntry`
     - ``str``
     - Rich text with HTML formatting.
   * - :class:`~labapi.entry.entries.text.PlainTextEntry`
     - ``str``
     - Unformatted plain text.
   * - :class:`~labapi.entry.entries.attachment.AttachmentEntry`
     - ``Attachment``
     - File uploads such as images, documents, and data files.

Inspect What You Created
------------------------

Access entries through the page's ``entries`` collection:

.. code-block:: python

   for entry in page.entries:
       print(f"Type: {entry.content_type}")
       print(f"Content: {entry.content}")

   first_entry = page.entries[0]

Related Pages
-------------

- :ref:`navigating` for locating a target page before adding entries.
- :ref:`entries` for how each entry class stores, updates, and returns content.
- :ref:`uploading_files` for attachment-specific details.
