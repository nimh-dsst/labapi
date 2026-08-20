.. _entries:

Working with Entries
====================

A LabArchives page contains entries for rich text, plain text, headers, file attachments, and widgets.

Accessing Entries
-----------------

A :class:`~labapi.tree.page.NotebookPage` exposes ``entries``, an :class:`~labapi.entry.collection.Entries` sequence.

.. code-block:: python

   page = notebook.traverse("Project A/Experiment 1/Results")
   
   # Get the number of entries
   print(len(page.entries))
   
   # Iterate over entries
   for entry in page.entries:
       print(f"ID: {entry.id}, Type: {entry.content_type}")
   
   # Access an entry by index
   first_entry = page.entries[0]

Entry Metadata
--------------

Entries loaded from a page or a search result carry read-only lifecycle
metadata when LabArchives supplies it:
:attr:`~labapi.entry.entries.base.Entry.created_at` and
:attr:`~labapi.entry.entries.base.Entry.updated_at` are
:class:`~datetime.datetime` objects parsed from the API's ISO-8601 timestamps,
and :attr:`~labapi.entry.entries.base.Entry.version` is an integer.

.. code-block:: python

   entry = page.entries[0]

   if entry.updated_at is not None:
       print(f"Last updated {entry.updated_at:%Y-%m-%d %H:%M %Z}")
   print(f"Version: {entry.version}")

.. note::
   All three are ``None`` when the API response omits them, and on entries you
   construct yourself rather than load from the API. Always check for ``None``
   before using them.

Searching Entries
-----------------

Use :meth:`~labapi.tree.notebook.Notebook.search` to search entries in a
notebook. It returns an :class:`~labapi.tree.search.EntrySearch`, a lazy,
iterable sequence of result pages — no API request is made until you iterate
it or fetch a specific page. Each page contains the same entry classes used by
``page.entries``.

.. code-block:: python

   from labapi import TextEntry

   for result_page in notebook.search('"brown rat"', page_size=100):
       for entry in result_page.entries:
           if isinstance(entry, TextEntry):
               entry.content = entry.content.replace(
                   "brown rat",
                   "Rattus norvegicus",
               )

Iteration fetches consecutive pages until every match has been returned, and
yields nothing when there are no matches.

Each result page is an :class:`~labapi.tree.search.EntrySearchPage` that
carries the matched entries along with result metadata. You can also fetch a
single page on demand with :meth:`~labapi.tree.search.EntrySearch.page`
instead of iterating:

.. code-block:: python

   search = notebook.search("Rattus norvegicus")  # page_size defaults to 25

   first_page = search.page(0)  # page numbers are zero-based
   print(f"{first_page.total_found} matching entries in the notebook")
   print(f"{first_page.total_returned} entries on this page")

:meth:`~labapi.tree.search.EntrySearch.page` raises :class:`IndexError` for
negative or out-of-range page numbers, and
:meth:`~labapi.tree.notebook.Notebook.search` raises :class:`ValueError` if
``page_size`` is not positive.

The search request itself is read-only. Returned entries use the same
``content`` accessors and setters as entries loaded from ``page.entries``.

Entry Types
-----------

LabArchives supports several entry types. In ``labapi``, each type is represented by a class inheriting from :class:`~labapi.entry.entries.base.Entry`.

Text-based Entries
~~~~~~~~~~~~~~~~~~

Text-based entries store their content as strings.

* **Rich Text Entry** (:class:`~labapi.entry.entries.text.TextEntry`): Used for formatted text, typically HTML. Content type: ``"text entry"``. See `MDN HTML documentation <https://developer.mozilla.org/en-US/docs/Web/HTML>`_ for HTML syntax.
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
   Widget entries are currently read-only in ``labapi``.

If LabArchives returns an entry type that ``labapi`` does not model,
:attr:`~labapi.tree.page.NotebookPage.entries` wraps unrecognized part types as
:class:`~labapi.entry.entries.unknown.UnknownEntry` and
recognized-but-unimplemented types as
:class:`~labapi.entry.entries.unknown.UnimplementedEntry`, each with a warning,
instead of silently dropping them.

Creating New Entries
--------------------

Call :meth:`~labapi.entry.collection.Entries.create` to add an entry to a page.

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

Create an :class:`~labapi.entry.attachment.Attachment` object, then pass it to :meth:`~labapi.entry.collection.Entries.create`.

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

A common pattern is to store structured data as a JSON attachment with a formatted preview in a companion text entry. :meth:`~labapi.entry.collection.Entries.create_json_entry` creates both in one call.

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

Assigning to ``entry.content`` sends an update request to LabArchives. Unknown, unimplemented, and widget entries do not support updates and raise :class:`NotImplementedError`.

.. code-block:: python

   entry = page.entries[0]
   entry.content = "New content for the entry"

For attachments, assign a new :class:`~labapi.entry.attachment.Attachment` to ``attachment_entry.content`` to replace the uploaded file.

.. code-block:: python

   new_attachment = Attachment.from_file("updated_data.csv")
   attachment_entry.content = new_attachment

Related Pages
-------------

* :ref:`writing_rich_text` for practical HTML-rich text snippets.
* :ref:`creating_pages` for page creation workflows before entry insertion.
* :doc:`/examples/csv_table` for CSV-to-HTML entry conversion patterns.
* :ref:`limitations` for current entry-type caveats.
