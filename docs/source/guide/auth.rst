.. _auth:
.. _authflow:

Authentication
==============

Authentication is handled by LabArchives. ``labapi`` works with two input patterns:

- callback-based authentication, where LabArchives redirects back with
  ``email`` and ``auth_code``
- manually copied External App credentials from the LabArchives UI

Use :meth:`~labapi.client.Client.login` for either pattern. Prefer
callback-based authentication for user sign-ins, especially when SSO is
required.

Choosing an Auth Pattern
------------------------

Use the flow that matches where your code runs:

.. list-table::
   :header-rows: 1

   * - Scenario
     - Recommended approach
     - Why
   * - Local scripts, notebooks, ad-hoc analysis on a workstation
     - :meth:`~labapi.client.Client.default_authenticate`
     - No callback wiring or manual credential copying; handles the browser round-trip automatically.
   * - Headless hosts (containers, CI workers, cron jobs, orchestrators)
     - :meth:`~labapi.client.Client.generate_auth_url` + callback handler + :meth:`~labapi.client.Client.login`
     - Avoids dependence on a local browser session.
   * - One-off/manual testing without callback wiring
     - :meth:`~labapi.client.Client.login` with External App credentials
     - Credentials are copied from the LabArchives UI; no browser or callback listener needed.

Interactive Authentication
--------------------------

For local interactive use, call
:meth:`~labapi.client.Client.default_authenticate`. It opens or prints a
LabArchives login URL, starts a temporary local callback server, and logs in
after LabArchives redirects back.

.. note:: 
    When the :ref:`optional-deps` are installed, this method can open a
    compatible local browser automatically. Without ``builtin-auth``, it still
    works in terminal/manual mode by printing the authentication URL.

.. code-block:: python

    from labapi import Client

    with Client() as client:
        user = client.default_authenticate()


Server-Based Authentication
---------------------------

For web apps and service integrations, call
:meth:`~labapi.client.Client.generate_auth_url` with your callback URL.
LabArchives redirects to that callback with ``email`` and ``auth_code``, and
your server passes those values to :meth:`~labapi.client.Client.login`.

The flow:

1. Your app exposes a callback URL (for example ``https://my-service.example.org/labarchives/callback``).
2. Your app sends users to ``client.generate_auth_url(callback_url)``.
3. LabArchives redirects back to your callback URL with ``email`` and ``auth_code`` query parameters.
4. Your callback handler exchanges those values via :meth:`~labapi.client.Client.login`.
5. Your service stores only what it needs for subsequent calls, following your organization's secret-management policy.

.. note::
   ``labapi`` currently does not provide a separate client-credentials style service principal flow.
   Service integrations should use callback-based login for user context. Use External App authentication only when the job can manage a short-lived External App auth code.


Example Flask App
-----------------

.. code-block:: python

    import flask
    from labapi import Client

    app = flask.Flask(__name__)

    @app.route("/login")
    def login():
        with Client() as client:
            callback_url = flask.url_for("callback", _external=True)
            auth_url = client.generate_auth_url(callback_url)
            return flask.redirect(auth_url)

    @app.route("/callback")
    def callback():
        email = flask.request.args.get("email")
        auth_code = flask.request.args.get("auth_code")

        if not email or not auth_code:
            return "Authentication failed.", 400

        with Client() as client:
            user = client.login(email, auth_code)
            notebook_names = list(user.notebooks)
            return f"Logged in as {user.id}. Notebooks: {notebook_names}"

    if __name__ == "__main__":
        app.run(port=8080)


Advanced Local Callback Control
-------------------------------

If you want to keep browser handling separate from callback capture, use
:meth:`~labapi.client.Client.generate_auth_url` and
:meth:`~labapi.client.Client.collect_auth_response` directly:

.. code-block:: python

    from labapi import Client

    with Client() as client:
        callback_path = "/auth/local-demo/"
        auth_url = client.generate_auth_url(
            f"http://127.0.0.1:8089{callback_path}"
        )

        with client.collect_auth_response(
            port=8089,
            callback_path=callback_path,
        ) as auth_response_collector:
            print("Open authentication URL in your browser:")
            print(auth_url)
            user = auth_response_collector.wait()

Headless and CI Workflows
-------------------------

In non-interactive environments (CI, scheduled jobs, or batch workers), avoid :meth:`~labapi.client.Client.default_authenticate` because it expects a browser and a local callback listener.

For scheduled jobs, pass a short-lived ``auth_code`` to :meth:`~labapi.client.Client.login` directly:

.. code-block:: bash

    export API_URL="https://api.labarchives.com"
    export ACCESS_KEYID="your_access_key"
    export ACCESS_PWD="your_access_password"
    export AUTH_EMAIL="service.user@example.org"
    export AUTH_KEY="short_lived_auth_code"

.. code-block:: python

    import os
    from labapi import Client

    client = Client()
    user = client.login(
        os.environ["AUTH_EMAIL"],
        os.environ["AUTH_KEY"],
    )

    # continue your automated task...
    # notebook = user.notebooks["Automation Notebook"]

.. note::

   ``AUTH_EMAIL`` and ``AUTH_KEY`` here are application-level environment
   variable names chosen by this example. Unlike ``API_URL``,
   ``ACCESS_KEYID``, and ``ACCESS_PWD``, they are not auto-loaded by
   :class:`~labapi.client.Client`.

Operational guidance for automation:

- Treat ``auth_code`` values as secrets; keep them in your CI secret store rather than source control.
- Prefer short-lived credentials, and define how the job obtains a new External App auth code before the current one expires.
- Use least-privilege LabArchives users for automated jobs.

Related Pages
-------------

* :ref:`first_calls` to sign in and run your first notebook operations.
* :ref:`faq` for browser selection and TLS troubleshooting during authentication.
* :ref:`limitations`
