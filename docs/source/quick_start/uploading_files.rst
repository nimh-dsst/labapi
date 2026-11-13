.. _uploading_files:

Uploading Files
===============

To upload an attachment, create an
:class:`~labapi.entry.attachment.Attachment` and then create an attachment
entry on the target page. The examples below assume you already have a
``page`` object.

Create an Attachment
--------------------

Build an :class:`~labapi.entry.attachment.Attachment` from a file path:

.. code-block:: python

   from labapi import Attachment

   attachment = Attachment.from_file("my_file.txt")

.. note::
   :meth:`~labapi.entry.attachment.Attachment.from_file` accepts a path or a
   seekable binary file object that has a ``name`` attribute.

If the MIME type cannot be determined from the filename, ``labapi`` falls back
to ``application/octet-stream``.

Check Upload Limits
-------------------

``get_max_upload_size()`` returns your account's upload limit in bytes:

.. code-block:: python

   max_size_bytes = page.user.get_max_upload_size()
   print(f"Max upload size: {max_size_bytes / 1024 / 1024:.1f} MB")

Upload the Attachment
---------------------

Pass it to :class:`~labapi.entry.entries.attachment.AttachmentEntry`:

.. code-block:: python

   from labapi import AttachmentEntry

   attachment_entry = page.entries.create(AttachmentEntry, attachment)

How Uploaded Files Appear
-------------------------

LabArchives displays uploaded files differently depending on their type:

- Images are shown inline with their caption beneath the image.
- PDFs are shown with a preview thumbnail and download link.
- Other file types are shown as downloadable links with an icon and caption.

Set a Custom Caption
--------------------

If you want a specific caption, construct the
:class:`~labapi.entry.attachment.Attachment` manually:

.. code-block:: python

   from labapi import Attachment, AttachmentEntry

   with open("experiment_results.png", "rb") as f:
       attachment = Attachment(
           backing=f,
           mime_type="image/png",
           filename="experiment_results.png",
           caption="Figure 1: Temperature vs. reaction rate at different pH levels",
       )

       figure_entry = page.entries.create(AttachmentEntry, attachment)

Related Pages
-------------

- :ref:`creating_pages` for creating pages before adding entries.
- :ref:`entries` for attachment entry behavior and update semantics.
- :ref:`limitations` for known limitations.
