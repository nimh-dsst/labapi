.. _example_csv_table:

CSV Table Upload/Download
=========================

This example uploads a CSV file as a LabArchives rich-text HTML table and
downloads table entries back to CSV.

When to Use It
--------------

Use it to publish CSV results in notebook pages and retrieve table entries for
downstream analysis.

Requirements
------------

This example assumes the recommended local interactive profile,
``labapi[dotenv,builtin-auth]``. See :ref:`installation`.

It also requires ``beautifulsoup4`` for HTML table parsing during download.

Configuration
-------------

For local interactive use, create a ``.env`` file in the repository root:

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

Upload Flow
~~~~~~~~~~~

- Read CSV data from disk.
- Convert it to HTML table markup.
- Upload the HTML as a rich-text entry.

Download Flow
~~~~~~~~~~~~~

- Find a text entry containing an HTML table.
- Parse the table back into structured data.
- Write the result to a CSV file.

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
- For simple tables, rows and columns are preserved when converting CSV to
  HTML and back; leading and trailing whitespace inside cells is stripped on
  download.
- Multiple table entries on one page are supported; by default, download
  selects the newest text entry containing a table.
- Empty cells in CSV files are preserved in the HTML table.
- Save non-ASCII CSV files as UTF-8.
- Complex nested tables are not supported.
- Only the first table is extracted if an entry contains multiple tables.

Ways to Extend It
-----------------

1. Export multiple tables from one page to separate CSV files.
2. Handle ``colspan`` and ``rowspan`` attributes.
3. Validate CSV structure before upload.
4. Read from and write to XLSX files.
5. Generate charts from CSV data and upload them as images.
6. Support HTML table captions.

Source Code
-----------

.. literalinclude:: ../../../examples/csv_table/csv_table.py
   :language: python

Related Pages
-------------

- :doc:`index` for the full examples catalog.
- :ref:`writing_rich_text` for the underlying HTML entry model.
- :ref:`first_calls` for local authentication setup.
