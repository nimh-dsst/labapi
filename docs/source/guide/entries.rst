.. _entries:

Working with Entries
====================

Entries are the fundamental building blocks of a LabArchives page. They contain the actual data, such as rich text, plain text, headers, file attachments, and widgets.

Accessing Entries
-----------------

You can access the entries of a :class:`~labapi.tree.page.NotebookPage` through its ``entries`` property. This property returns an :class:`~labapi.entry.collection.Entries` object, which behaves like a sequence of entries.

.. code-block:: python

   page = notebook.traverse("Project A/Experiment 1/Results")
   
   # Get the number of entries
   print(len(page.entries))
   
   # Iterate over entries
   for entry in page.entries:
       print(f"ID: {entry.id}, Type: {entry.content_type}")
   
   # Access an entry by index
   first_entry = page.entries[0]

Searching Entries
-----------------

Use :meth:`~labapi.tree.notebook.Notebook.search` to search entries in a
notebook. Search returns an iterable of result pages, and each page contains
normal entry objects.

.. code-block:: python

   from labapi import TextEntry

   for result_page in notebook.search('"brown rat"', page_size=100):
       for entry in result_page.entries:
           if isinstance(entry, TextEntry):
               entry.content = entry.content.replace(
                   "brown rat",
                   "Rattus norvegicus",
               )

The search request itself is read-only. Returned entries use the same
``content`` accessors and setters as entries loaded from ``page.entries``.

Entry Types
-----------

LabArchives supports several entry types. In ``labapi``, each type is represented by a specific class inheriting from :class:`~labapi.entry.entries.base.Entry`.

Text-based Entries
~~~~~~~~~~~~~~~~~~

Text-based entries store their content as strings.

* **Rich Text Entry** (:class:`~labapi.entry.entries.text.TextEntry`): Used for formatted text, typically HTML. Content type: ``"text entry"``. See `MDN HTML documentation <https://developer.mozilla.org/en-US/docs/Web/HTML>`_ for supported markup patterns.
* **Plain Text Entry** (:class:`~labapi.entry.entries.text.PlainTextEntry`): Used for unformatted, raw text. Content type: ``"plain text entry"``.
* **Header Entry** (:class:`~labapi.entry.entries.text.HeaderEntry`): Used for headings or titles within a page. Content type: ``"heading"``.

.. code-block:: python

   # Accessing text content
   text_entry = page.entries[0]
   print(text_entry.content)

   # Updating rich text content
   text_entry.content = "<p>Updated <strong>rich text</strong> content</p>"

Attachment Entries
~~~~~~~~~~~~~~~~~~

Attachment entries (:class:`~labapi.entry.entries.attachment.AttachmentEntry`) represent file attachments. Their content is an :class:`~labapi.entry.attachment.Attachment` object.

.. code-block:: python

   attachment_entry = page.entries[1]
   attachment = attachment_entry.content
   
   print(f"Filename: {attachment.filename}")
   print(f"MIME Type: {attachment.mime_type}")
   print(f"Caption: {attachment.caption}")
   
   # Read the file data
   data = attachment.read()

Widget Entries
~~~~~~~~~~~~~~

Widget entries (:class:`~labapi.entry.entries.widget.WidgetEntry`) embed interactive content or external applications. Like text entries, their content is represented as a string (often JSON or HTML).

.. note::
   Widget entries are currently read-only in ``labapi``. Their ``content`` property returns the widget's internal data as a JSON-formatted string.

If LabArchives returns an entry type that ``labapi`` does not model yet,
:attr:`~labapi.tree.page.NotebookPage.entries` wraps it as
:class:`~labapi.entry.entries.unknown.UnknownEntry` and emits a warning instead
of silently dropping it.

Creating New Entries
--------------------

You can create new entries using the :meth:`~labapi.entry.collection.Entries.create` method.

.. code-block:: python

   from labapi import TextEntry, HeaderEntry, PlainTextEntry

   # Create a rich text entry (HTML is rendered in LabArchives)
   page.entries.create(TextEntry, "<h2>New Section</h2><p>Some <em>formatted</em> content...</p>")

   # Create a heading (displayed as a section label/divider)
   page.entries.create(HeaderEntry, "Experiment Notes")

   # Create a plain text entry (displayed literally)
   page.entries.create(PlainTextEntry, "<h2>Raw instrument output</h2>")

Creating Attachments
~~~~~~~~~~~~~~~~~~~~

To create an attachment entry, you first need to create an :class:`~labapi.entry.attachment.Attachment` object.

.. code-block:: python

   from io import BytesIO
   from labapi import Attachment, AttachmentEntry
   
   # Create attachment from in-memory data
   data = BytesIO(b"Hello, LabArchives!")
   attachment = Attachment(data, "text/plain", "hello.txt", "A simple text file")
   
   # Upload as a new entry
   page.entries.create(AttachmentEntry, attachment)

You can also create an attachment directly from a file on disk:

.. code-block:: python

   from labapi import Attachment, AttachmentEntry

   attachment = Attachment.from_file("data.csv")
   page.entries.create(AttachmentEntry, attachment)

``Attachment.from_file()`` accepts a filesystem path (string or ``Path``) or a
random-access binary file object.

Working with JSON Data
----------------------

A common pattern is to store structured data as a JSON attachment with a formatted preview in a companion text entry. The :meth:`~labapi.entry.collection.Entries.create_json_entry` method simplifies this.

.. code-block:: python

   data = {
       "experiment_id": "EXP-123",
       "results": [1.2, 3.4, 5.6],
       "status": "complete"
   }
   
   # Creates both an attachment entry and a text entry preview
   file_entry, text_entry = page.entries.create_json_entry(data)

Modifying Entries
-----------------

To modify an entry, simply set its ``content`` property. The change is automatically synchronized with the LabArchives server.

.. code-block:: python

   entry = page.entries[0]
   entry.content = "New content for the entry"

For attachments, setting the ``content`` property with a new :class:`~labapi.entry.attachment.Attachment` object will update the file.

.. code-block:: python

   new_attachment = Attachment.from_file("updated_data.csv")
   attachment_entry.content = new_attachment

Related Pages
-------------

* :ref:`writing_rich_text` for practical HTML-rich text snippets.
* :ref:`creating_pages` for page creation workflows before entry insertion.
* :doc:`/examples/csv_table` for CSV-to-HTML entry conversion patterns.
* :ref:`limitations` for current entry-type caveats.
