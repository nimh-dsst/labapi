.. _installation:

Installation
============

Install ``labapi`` with the extras you need, then configure credentials with
``.env`` or environment variables.

Python Version
--------------

Supports Python 3.10 and newer.

Choose an Install Profile
-------------------------

Choose the install target that includes the helpers you need:

.. list-table::
   :header-rows: 1

   * - Profile
     - Install Target
     - Use When
   * - Recommended local interactive
     - ``labapi[dotenv,builtin-auth]``
     - You want ``.env`` loading and browser-based ``default_authenticate()``
       for local examples.
   * - Minimal
     - ``labapi``
     - You already manage environment variables or pass credentials directly,
       and you do not need optional helpers.
   * - Minimal + ``.env`` loading
     - ``labapi[dotenv]``
     - You want :class:`~labapi.client.Client` to read a local ``.env`` file,
       but you do not need browser helpers.

.. tab-set::

   .. tab-item:: uv

      .. code-block:: bash

         uv add "labapi[dotenv,builtin-auth]"
         uv add labapi
         uv add "labapi[dotenv]"

   .. tab-item:: poetry

      .. code-block:: bash

         poetry add "labapi[dotenv,builtin-auth]"
         poetry add labapi
         poetry add "labapi[dotenv]"

   .. tab-item:: pip

      .. code-block:: bash

         pip install "labapi[dotenv,builtin-auth]"
         pip install labapi
         pip install "labapi[dotenv]"

.. _optional-deps:

Optional Extras
---------------

``labapi`` has two optional extras:

- ``dotenv`` lets :class:`~labapi.client.Client` read ``API_URL``,
  ``ACCESS_KEYID``, and ``ACCESS_PWD`` from a local ``.env`` file.
- ``builtin-auth`` lets
  :meth:`~labapi.client.Client.default_authenticate` auto-detect and open a
  local browser. Without it, you can still use terminal/manual auth or your own
  callback flow.

Configuration
-------------

If you installed ``dotenv``, create a local ``.env`` file:

.. code-block:: toml

   API_URL="https://api.labarchives.com"
   ACCESS_KEYID="your_access_key"
   ACCESS_PWD="your_access_password"

If you did not install ``dotenv``, set those values directly in your shell
before running your code:

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

Related Pages
-------------

- :ref:`first_success_tutorial` for the runnable first script.
- :ref:`first_calls` for authentication and notebook access patterns.
- :ref:`faq` for browser and certificate troubleshooting.
