.. _examples:

Example Applications
====================

These examples show complete scripts for JSON sync, folder export, and CSV
table conversion. Start with :ref:`installation` if you still need to set up
the recommended local interactive profile.

.. toctree::
   :maxdepth: 1
   :hidden:

   json_sync
   folder_download
   csv_table

Example Matrix
--------------

.. list-table::
   :header-rows: 1

   * - Example
     - Best For
     - Extra Packages
   * - :doc:`json_sync`
     - Uploading JSON files to a page and downloading JSON attachments back to
       disk
     - none
   * - :doc:`folder_download`
     - Exporting notebook pages and entries to local files for backup or
       review
     - none
   * - :doc:`csv_table`
     - Converting CSV data to LabArchives HTML tables and back to CSV
     - ``beautifulsoup4``

Getting Started
---------------

All published examples assume:

- Python 3.10+.
- The recommended local interactive profile:
  ``labapi[dotenv,builtin-auth]``.
- Run the ``uv run --project ...`` commands below from the repository root.
- Use page paths relative to the notebook root, together with
  ``--notebook "My Notebook"``.

Use these sample commands as starting points:

.. code-block:: bash

   uv run --project examples/json_sync python examples/json_sync/json_sync.py upload examples/json_sync/sample_data "Experiments/2024/Data Analysis" --notebook "My Notebook"
   uv run --project examples/folder_download python examples/folder_download/folder_download.py ./backup --notebook "My Notebook" --path "Experiments/2024"
   uv run --project examples/csv_table python examples/csv_table/csv_table.py upload examples/csv_table/sample_data.csv "Experiments/Results" --notebook "My Notebook"

Additional Local Examples
-------------------------

The repository also includes ``examples/model_logging`` and
``examples/notebook_logging``. They are maintained in the repository but are
not covered by these Sphinx example pages.

Related Pages
-------------

- :ref:`installation` for package-manager commands and optional extras.
- :ref:`first_calls` for credential and authentication setup.
- :ref:`guide` for the behavior behind these workflows.
