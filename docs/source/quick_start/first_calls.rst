.. _first_calls:

Your First Entry
================

Install ``labapi`` first; see :ref:`installation`.

.. _obtaining_api_keys:

Obtain API Keys
---------------

Every request to the LabArchives API is signed with an Access Key ID
(``akid``) and Access Password issued by LabArchives. These identify your
application; signing in (below) identifies the user. LabArchives issues API
keys only on request:

- If your institution has a LabArchives enterprise license, ask your
  institution's LabArchives site administrator (or your LabArchives Enterprise
  Success Team contact) to request API access. Provide the name and email
  address for each existing LabArchives account that needs API access.
- Otherwise, contact LabArchives support at
  `support@labarchives.com <mailto:support@labarchives.com>`_.

LabArchives also tells you the API base URL for your region. These docs use
``https://api.labarchives.com``, the URL for US-hosted accounts.

Create a Client
---------------

:class:`~labapi.client.Client` takes the API URL, Access Key ID, and Access
Password from a ``.env`` file, environment variables, or constructor arguments:

.. tab-set::

   .. tab-item:: With ``.env`` (Recommended)
      :sync: env-file

      Create a ``.env`` file in your project directory:

      .. code-block:: toml

         API_URL="https://api.labarchives.com"
         ACCESS_KEYID="your_access_key"
         ACCESS_PWD="your_access_password"

      Then initialize the client directly:

      .. code-block:: python

         from labapi import Client

         client = Client()

      .. note::
         Loading ``.env`` requires the ``dotenv`` extra; see :ref:`installation`.

   .. tab-item:: Environment Variables
      :sync: env-vars

      Set the environment variables before running your script.

      .. tab-set::

         .. tab-item:: Bash

            .. code-block:: bash

               export API_URL="https://api.labarchives.com"
               export ACCESS_KEYID="your_access_key"
               export ACCESS_PWD="your_access_password"

         .. tab-item:: PowerShell

            .. code-block:: powershell

               $env:API_URL="https://api.labarchives.com"
               $env:ACCESS_KEYID="your_access_key"
               $env:ACCESS_PWD="your_access_password"

         .. tab-item:: Command Prompt

            .. code-block:: bat

               set API_URL=https://api.labarchives.com
               set ACCESS_KEYID=your_access_key
               set ACCESS_PWD=your_access_password

      In Python:

      .. code-block:: python

         from labapi import Client

         client = Client()

   .. tab-item:: Constructor Arguments
      :sync: explicit

      You can also pass the credentials directly when creating the client:

      .. code-block:: python

         from labapi import Client

         client = Client(
             base_url="https://api.labarchives.com",
             akid="your_access_key",
             akpass="your_access_password",
         )

Sign In
-------

Local Interactive Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Call :meth:`~labapi.client.Client.default_authenticate` to sign in through a
browser on the same machine.

.. code-block:: python

   from labapi import Client

   with Client() as client:
       user = client.default_authenticate()

.. note::
   With the ``builtin-auth`` extra, ``labapi`` opens the browser for you. If it
   cannot, it prints a URL for you to open yourself.

External App Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you cannot use a browser on the same machine, or for a manual login test,
use an External App authentication code:

1. Log in to your LabArchives account in a web browser.
2. Click your name in the top-right corner and select
   **External App authentication**.
3. Copy the email address and password token, then pass them to
   :meth:`~labapi.client.Client.login`.

.. code-block:: python

   from labapi import Client

   client = Client()
   user = client.login("your.email@example.com", "YOUR_AUTH_CODE")

.. note::
   The External App password token is valid for only one hour.

Service and Non-Interactive Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Backend systems, scheduled jobs, and CI pipelines cannot open a local browser.
Use this flow instead:

1. In your web or service layer, redirect users to
   ``client.generate_auth_url(callback_url)``.
2. Capture ``email`` and ``auth_code`` from the callback request.
3. Exchange those values via :meth:`~labapi.client.Client.login`.

For the complete flow, see :ref:`auth`.

Get a Notebook
--------------

Once you have a :class:`~labapi.user.User` object, you can access notebooks by
name or iterate over them:

.. code-block:: python

   notebook = user.notebooks["My Notebook"]

   for notebook_name in user.notebooks:
       print(notebook_name)

   for notebook in user.notebooks.values():
       print(notebook.name, notebook.id)

Write Entries
-------------

The entry class decides how LabArchives shows the content:

- :class:`~labapi.entry.entries.text.TextEntry` renders HTML formatting.
- :class:`~labapi.entry.entries.text.PlainTextEntry` preserves text
  literally.
- :class:`~labapi.entry.entries.text.HeaderEntry` creates a visible section
  divider.

.. code-block:: python

   from labapi import HeaderEntry, PlainTextEntry, TextEntry

   page = notebook.traverse("Experiments/Project A/Results")

   page.entries.create(TextEntry, "<p><strong>Trial 1:</strong> Successfully ran.</p>")
   page.entries.create(PlainTextEntry, "<strong>Raw instrument log line</strong>")
   page.entries.create(HeaderEntry, "Follow-up Measurements")

Related Pages
-------------

- :ref:`auth` for full interactive and server-side authentication flows.
- :ref:`navigating` for path-based notebook traversal after login.
- :ref:`entries` for how entry classes store and update content.
