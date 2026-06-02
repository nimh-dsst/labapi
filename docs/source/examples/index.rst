.. _examples:

Example Applications
====================

These runnable examples show end-to-end workflows built on top of the core
``labapi`` APIs. Start with :ref:`installation` if you still need to set up the
recommended local interactive profile.

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
     - Syncing JSON attachments and previews between a local folder and a
       LabArchives page
     - none
   * - :doc:`folder_download`
     - Exporting notebook structure to local files for backup, review, or
       archival
     - none
   * - :doc:`csv_table`
     - Converting CSV data to LabArchives HTML tables and round-tripping back
       to CSV
     - ``beautifulsoup4``

Published Examples
------------------

- :doc:`json_sync` synchronizes JSON files between a local folder and a single
  LabArchives page.
- :doc:`folder_download` mirrors a notebook subtree to local files while
  preserving page and directory structure.
- :doc:`csv_table` uploads CSV data as HTML tables and downloads those tables
  back to CSV.

Getting Started
---------------

All published examples assume:

- Python 3.10+.
- The recommended local interactive profile:
  ``labapi[dotenv,builtin-auth]``.
- A repository-root working directory when you run the ``uv run --project ...``
  commands below.
- Notebook-relative page paths paired with ``--notebook "My Notebook"``.

Use these sample commands as known-good starting points:

.. code-block:: bash

   uv run --project examples/json_sync python examples/json_sync/json_sync.py upload examples/json_sync/sample_data "Experiments/2024/Data Analysis" --notebook "My Notebook"
   uv run --project examples/folder_download python examples/folder_download/folder_download.py ./backup --notebook "My Notebook" --path "Experiments/2024"
   uv run --project examples/csv_table python examples/csv_table/csv_table.py upload examples/csv_table/sample_data.csv "Experiments/Results" --notebook "My Notebook"

Additional Local Examples
-------------------------

The repository also includes ``examples/model_logging`` and
``examples/notebook_logging``. They are maintained alongside the published
examples above, but do not yet have dedicated Sphinx pages.

Related Pages
-------------

- :ref:`installation` for package-manager commands and optional extras.
- :ref:`first_calls` for credential and authentication setup.
- :ref:`guide` for the behavior behind these workflows.
