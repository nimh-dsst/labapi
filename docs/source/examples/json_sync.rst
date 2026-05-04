.. _example_json_sync:

JSON Folder Sync
================

This example syncs JSON content between a local folder and a LabArchives page.
Use it when you want a simple batch workflow for moving structured JSON files
in or out of a notebook page.

When to Use It
--------------

This is useful for:

- Backing up structured data from LabArchives to your local machine.
- Uploading batches of JSON data files to a LabArchives page.
- Syncing experimental data stored as JSON between local files and LabArchives.
- Archiving API responses or other structured datasets.

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

Upload the sample JSON files included in the repository:

.. code-block:: bash

   uv run --project examples/json_sync python examples/json_sync/json_sync.py upload examples/json_sync/sample_data "Experiments/2024/Data Analysis" --notebook "My Notebook"

Download JSON entries from a page into a local folder:

.. code-block:: bash

   uv run --project examples/json_sync python examples/json_sync/json_sync.py download "Experiments/2024/Data Analysis" ./output --notebook "My Notebook"

How It Works
------------

- JSON files are uploaded with
  :meth:`~labapi.entry.collection.Entries.create_json_entry`.
- ``examples/json_sync/json_sync.py`` contains importable upload and download
  functions plus a command-line ``main()`` guarded by the usual
  ``if __name__ == "__main__"`` check.
- Each upload creates a JSON attachment with ``application/json`` MIME type and
  a companion rich-text preview entry.
- Download mode writes each JSON attachment back to a local ``.json`` file.

Reusable API
------------

When building your own script, import the sync function and call it directly:

.. code-block:: python

   from pathlib import Path

   from labapi import Client
   from examples.json_sync.json_sync import upload_json_files

   with Client() as client:
       user = client.default_authenticate()
       results = upload_json_files(
           user,
           notebook="My Notebook",
           page="Experiments/2024/Data Analysis",
           folder=Path("examples/json_sync/sample_data"),
       )

   uploaded = sum(result.success for result in results)
   print(f"Uploaded {uploaded}/{len(results)} JSON files")

Notes and Limitations
---------------------

- Invalid JSON files are skipped with an error message.
- The script creates the output folder if it does not exist during download.
- The reusable functions return a ``FileResult`` for each file they try to sync.
- The CLI handles terminal output and process exit codes.
- The sample upload command uses the checked-in files under
  ``examples/json_sync/sample_data``.

Ways to Extend It
-----------------

1. Implement diff-based sync so only changed files are uploaded.
2. Recurse through subdirectories instead of processing a single folder.
3. Add filename filtering for larger datasets.
4. Show progress bars with ``tqdm``.
5. Add retry logic for failed uploads and downloads.

Source Code
-----------

.. literalinclude:: ../../../examples/json_sync/json_sync.py
   :language: python

Related Pages
-------------

- :doc:`index` for the full examples catalog.
- :doc:`/guide/json_entries` for the JSON attachment + preview model.
- :ref:`first_calls` for local authentication setup.
