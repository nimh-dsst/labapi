.. _example_csv_table:

CSV Table Upload/Download
=========================

This example uploads a CSV file as a LabArchives rich-text HTML table and
downloads table entries back to CSV.

Requirements
------------

Install ``labapi[dotenv,builtin-auth]`` (see :ref:`installation`) and
``beautifulsoup4``, which parses HTML tables during download.

Configuration
-------------

Create a ``.env`` file in the repository root:

.. code-block:: toml

   API_URL="https://api.labarchives.com"
   ACCESS_KEYID="your_access_key_id"
   ACCESS_PWD="your_password"

You can also provide the same values through shell environment variables. See
:ref:`first_calls` for both options.

How It Works
------------

``examples/csv_table/csv_table.py`` defines typed upload/download options,
converts CSV rows to HTML table markup, and parses table entries back to CSV.

Common Commands
---------------

Set up the example project:

.. code-block:: bash

   cd examples/csv_table
   uv sync

Upload the checked-in sample CSV file:

.. code-block:: bash

   uv run python csv_table.py upload sample_data.csv "Experiments/Results" --notebook "My Notebook"

Upload a CSV file without treating the first row as a header:

.. code-block:: bash

   uv run python csv_table.py upload sample_data.csv "Experiments/Results" --notebook "My Notebook" --no-header

Download the newest text entry on a page that contains an HTML table:

.. code-block:: bash

   uv run python csv_table.py download "Experiments/Results" results.csv --notebook "My Notebook"

Download a table from a specific zero-based page entry index:

.. code-block:: bash

   uv run python csv_table.py download "Experiments/Results" results.csv --notebook "My Notebook" --entry-index 2

Example CSV Input
-----------------

Given this CSV file (``examples/csv_table/sample_data.csv``):

.. code-block:: text

   Experiment,Temperature,Pressure,Result
   Trial 1,25.0,101.3,Success
   Trial 2,30.0,101.3,Success
   Trial 3,35.0,102.1,Failure

The script will generate this HTML table:

.. code-block:: html

   <table>
     <thead>
       <tr>
         <th>Experiment</th>
         <th>Temperature</th>
         <th>Pressure</th>
         <th>Result</th>
       </tr>
     </thead>
     <tbody>
       <tr>
         <td>Trial 1</td>
         <td>25.0</td>
         <td>101.3</td>
         <td>Success</td>
       </tr>
       <tr>
         <td>Trial 2</td>
         <td>30.0</td>
         <td>101.3</td>
         <td>Success</td>
       </tr>
       <tr>
         <td>Trial 3</td>
         <td>35.0</td>
         <td>102.1</td>
         <td>Failure</td>
       </tr>
     </tbody>
   </table>

Notes and Limitations
---------------------

- Tables are rendered with LabArchives' default styling and no inline CSS.
- Leading and trailing whitespace inside cells is stripped on download.
- By default, download selects the newest text entry containing a table.
- Save non-ASCII CSV files as UTF-8.
- Nested tables are not supported.
- Only the first table is extracted if an entry contains multiple tables.

Source Code
-----------

.. literalinclude:: ../../../examples/csv_table/csv_table.py
   :language: python

Related Pages
-------------

- :doc:`index` for the full examples catalog.
- :ref:`writing_rich_text` for the underlying HTML entry model.
- :ref:`first_calls` for local authentication setup.
