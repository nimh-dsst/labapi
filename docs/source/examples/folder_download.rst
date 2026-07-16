.. _example_folder_download:

Folder Structure Download
=========================

This example exports a notebook, folder, or page to local directories.
LabArchives directories and pages become local directories, and individual
entries are written out as separate files.

When to Use It
--------------

Use it to create local backup, offline review, archival, migration, or
version-control copies of notebook content.

Requirements
------------

This example assumes the recommended local interactive profile,
``labapi[dotenv,builtin-auth]``. See :ref:`installation`.

No additional third-party packages are required.

Configuration
-------------

For the local interactive workflow, create a ``.env`` file in the repository
root:

.. code-block:: toml

   API_URL="https://api.labarchives.com"
   ACCESS_KEYID="your_access_key_id"
   ACCESS_PWD="your_password"

You can also provide the same values through shell environment variables. See
:ref:`first_calls` for both options.

Common Commands
---------------

Download an entire notebook:

.. code-block:: bash

   uv run --project examples/folder_download python examples/folder_download/folder_download.py ./backup --notebook "My Notebook"

Download only a specific subtree:

.. code-block:: bash

   uv run --project examples/folder_download python examples/folder_download/folder_download.py ./2024_experiments --notebook "My Notebook" --path "Experiments/2024"

Overwrite an existing output directory:

.. code-block:: bash

   uv run --project examples/folder_download python examples/folder_download/folder_download.py ./backup --notebook "My Notebook" --overwrite

How It Works
------------

``examples/folder_download/folder_download.py`` exposes
``download_notebook_or_folder(user, options)``, which writes the export and
returns a ``DownloadResult`` for callers.

The script mirrors the LabArchives structure:

.. code-block:: text

   LabArchives Structure:          Local File Structure:

   My Notebook/                    output/My Notebook/
   |- Experiments/                 |- Experiments/
   |  |- Trial 1/  (page)          |  |- Trial 1/
   |  |  |- Header entry           |  |  |- 001_header.txt
   |  |  |- Text entry             |  |  |- 002_text.html
   |  |  `- Attachment             |  |  `- 003_attachment_image.png
   |  `- Trial 2/  (page)          |  `- Trial 2/
   |     `- Text entry             |     `- 001_text.html
   `- Data/  (directory)           `- Data/
      `- Results/  (page)             `- Results/
         `- Attachment                  `- 001_attachment_data.csv

File Naming Convention
----------------------

Downloaded entries follow this naming pattern:

.. code-block:: text

   001_header.txt          # First entry (header)
   002_text.html           # Second entry (rich text)
   003_attachment_data.csv # Third entry (attachment)
   003_caption.txt         # Caption for the attachment
   004_plaintext.txt       # Fourth entry (plain text)

- Entries are numbered in the order they appear on the page.
- Entry type is indicated in the filename.
- Attachments preserve their original filename.
- When an attachment has a caption, it is saved in a separate
  ``*_caption.txt`` file.

Output Layout
-------------

The exported tree uses these files and subdirectories:

For pages:

- ``_metadata.txt`` with page information such as name, ID, and entry count.
- ``001_*``, ``002_*``, and similar files for each entry on the page.

For directories:

- A subdirectory for each child directory or page.

Notes
-----

- Filenames are sanitized to be filesystem-safe.
- Widget entries are exported as ``*_widget.txt`` placeholder notes; their
  content is not exported.
- Download time grows with notebook size and attachment count.

Reusable API
------------

Reuse the exporter by constructing ``DownloadFolderOptions`` and passing it to
``download_notebook_or_folder``:

.. code-block:: python

   from pathlib import Path

   from labapi import Client
   from examples.folder_download.folder_download import (
       DownloadFolderOptions,
       download_notebook_or_folder,
   )

   with Client() as client:
       user = client.default_authenticate()
       result = download_notebook_or_folder(
           user,
           DownloadFolderOptions(
               notebook_name="My Notebook",
               output_dir=Path("notebook_export"),
               path="Experiments/2024",
           ),
       )

   print(f"Downloaded {result.page_count} pages and {result.entry_count} entries")

Ways to Extend It
-----------------

1. Add resume capability for interrupted downloads.
2. Verify downloaded files with checksums.
3. Create ZIP archives after export.
4. Filter by entry type or date range.
5. Add progress bars with ``tqdm``.
6. Implement incremental backups for only new or changed content.
7. Export metadata as JSON.
8. Write detailed logs during long downloads.

Source Code
-----------

.. literalinclude:: ../../../examples/folder_download/folder_download.py
   :language: python

Related Pages
-------------

- :doc:`index` for the full examples catalog.
- :ref:`limitations` for export caveats and unsupported entry behavior.
- :ref:`first_calls` for local authentication setup.
