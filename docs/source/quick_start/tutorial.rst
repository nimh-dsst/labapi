.. _first_success_tutorial:

First Success Tutorial
======================

These steps create one visible text entry in LabArchives.

Install ``labapi``
------------------

Install ``labapi`` with the extras used throughout this tutorial:

.. tab-set::

   .. tab-item:: uv

      .. code-block:: bash

         uv add "labapi[dotenv,builtin-auth]"

   .. tab-item:: pip

      .. code-block:: bash

         pip install "labapi[dotenv,builtin-auth]"

See :ref:`installation` for the other install profiles.

Create a ``.env`` File
----------------------

Create a ``.env`` file in your project folder:

.. code-block:: toml

   API_URL="https://api.labarchives.com"
   ACCESS_KEYID="your_access_key"
   ACCESS_PWD="your_access_password"

Replace the values with your own LabArchives API credentials.

Run a Minimal Script
--------------------

Copy this script into ``first_success.py``. It uses the first notebook in
your account.

.. code-block:: python

   from datetime import datetime

   from labapi import Client, NotebookPage, TextEntry

   with Client() as client:
       user = client.default_authenticate()
       notebook_name = next(iter(user.notebooks))
       print(f"Using notebook {notebook_name}")
       notebook = user.notebooks[notebook_name]
       page = notebook.create(
           NotebookPage,
           f"API tutorial - {datetime.now():%Y-%m-%d %H:%M:%S}",
       )
       page.entries.create(TextEntry, "<p>Hello from labapi!</p>")
       print(f"Created page: {page.path}")

Then run it:

.. code-block:: bash

   python first_success.py

Confirm the Result
------------------

After the script finishes:

- The selected notebook contains a new page named
  ``API tutorial - <timestamp>``.
- Opening that page shows one text entry with the message
  ``Hello from labapi!``.

Related Pages
-------------

- :ref:`installation` for all install profiles.
- :ref:`first_calls` for more detail on credentials and authentication options.
- :ref:`creating_pages` for creating directories, pages, and entries.
