.. _example_json_sync:

JSON Folder Sync
================

This example uploads local ``*.json`` files to a LabArchives page and downloads
JSON attachment entries back to disk.

Requirements
------------

Install ``labapi[dotenv,builtin-auth]`` (see :ref:`installation`). No other
packages are needed.

Configuration
-------------

Create a ``.env`` file in the repository root:

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
- ``examples/json_sync/json_sync.py`` exposes importable upload and download
  functions and a CLI entry point.
- Each upload creates a JSON attachment with ``application/json`` MIME type and
  a companion rich-text preview entry.
- Download mode writes each JSON attachment back to a local file named after
  the attachment.

Reusable API
------------

To upload from your own script:

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
- Download creates the output folder if it is missing.
- The reusable functions return a ``FileResult`` for each JSON file processed,
  including failures.

Source Code
-----------

.. literalinclude:: ../../../examples/json_sync/json_sync.py
   :language: python

Related Pages
-------------

- :doc:`index` for the full examples catalog.
- :doc:`/guide/json_entries` for how JSON entries are stored.
- :ref:`first_calls` for local authentication setup.
