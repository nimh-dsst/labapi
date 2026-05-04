.. _example_csv_table:

CSV Table Upload/Download
=========================

This example uploads CSV data as rich-text HTML tables in LabArchives and can
download those tables back to CSV later. It is a good fit when you want
readable tables in the notebook UI without losing a machine-friendly export
path.

When to Use It
--------------

This is useful for:

- Uploading experimental data tables for visual display in notebooks.
- Creating formatted data tables that stay readable in the web interface.
- Extracting tabular data back to CSV for downstream analysis.
- Documenting datasets with consistent structure.
- Sharing tables with collaborators in a readable format.

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

The example is a single script. ``examples/csv_table/csv_table.py`` defines
small typed option objects, uses LabArchives page and entry APIs, and keeps
CSV/HTML conversion details inside the script.

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

Upload a CSV file with every row treated as table data:

.. code-block:: bash

   uv run python csv_table.py upload sample_data.csv "Experiments/Results" --notebook "My Notebook" --no-header

Download the most recent table from a page:

.. code-block:: bash

   uv run python csv_table.py download "Experiments/Results" results.csv --notebook "My Notebook"

Download a specific table entry by index:

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

The table is displayed with LabArchives' default styling.

Notes and Limitations
---------------------

- Tables are uploaded as rich-text entries, making them readable in the
  LabArchives web interface.
- Tables are rendered with LabArchives' default styling and no inline CSS.
- The script preserves table structure and can round-trip CSV to HTML and back
  to CSV.
- Multiple tables on one page are supported; by default, the download uses the
  most recent table.
- Empty cells in CSV files are preserved in the HTML table.
- CSV files with special characters should use UTF-8 encoding.
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

Source
------

.. literalinclude:: ../../../examples/csv_table/csv_table.py
   :language: python

Related Pages
-------------

- :doc:`index` for the full examples catalog.
- :ref:`writing_rich_text` for the underlying HTML entry model.
- :ref:`first_calls` for local authentication setup.
