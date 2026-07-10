.. _contributing:

Contributing
============

This page covers the local development workflow for ``labapi``: running tests,
enforcing code style, and following the project's type-system conventions.

Setup
-----

Install the package with its development dependencies using ``uv``:

.. code-block:: bash

   uv sync --all-groups
   pre-commit install --hook-type pre-commit --hook-type pre-push

Running Tests
-------------

The test suite is split into unit tests and integration tests. Plain
``pytest`` deselects integration tests by default.

Run the full suite, including integration tests, with:

.. code-block:: bash

   uv run pytest --integration

Unit Tests
~~~~~~~~~~

Unit tests use a ``MockClient`` that replays pre-recorded API responses, so
they run entirely offline.

.. code-block:: bash

   uv run pytest
   uv run pytest --no-cov
   uv run pytest tests/tree/test_mixins.py

Integration Tests
~~~~~~~~~~~~~~~~~

Integration tests hit the live LabArchives API and require credentials in the
environment or a ``.env`` file:

.. code-block:: text

   ACCESS_KEYID=your_akid
   ACCESS_PWD=your_password
   API_URL=https://api.labarchives.com

   AUTH_EMAIL=your@email.com
   AUTH_KEY=your_auth_key

   # Optional: use the browser callback flow instead
   # AUTH_INTERACTIVE=true

Run them explicitly with:

.. code-block:: bash

   uv run pytest --integration tests/test_integration.py

.. note::
   :class:`~labapi.client.Client` only auto-loads ``API_URL``,
   ``ACCESS_KEYID``, and ``ACCESS_PWD``. ``AUTH_EMAIL`` and ``AUTH_KEY`` are
   conventions used by this repository's integration-test fixtures.

Attachment Update 4999 Reproducer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The attachment-update ``4999`` reproducer is separately gated because it
creates and updates content through the live LabArchives API.

.. code-block:: bash

   LABAPI_RUN_ATTACHMENT_4999_REPRODUCER=true uv run pytest \
      --integration tests/test_integration.py \
      -k attachment_update_4999_reproducer -s

In PowerShell:

.. code-block:: powershell

   $env:LABAPI_RUN_ATTACHMENT_4999_REPRODUCER = "true"
   uv run pytest --integration tests/test_integration.py `
      -k attachment_update_4999_reproducer -s

The reproducer creates an isolated page and attachment, then updates the
attachment through ``AttachmentEntry.content``. It prints the request shape
and reports the API response if LabArchives returns ``4999``. Payload bytes
are represented by their length and SHA-256 hash rather than their contents.

Code Style
----------

``labapi`` uses `Ruff <https://docs.astral.sh/ruff/>`_ for both linting and
formatting.

Pre-commit Hooks
~~~~~~~~~~~~~~~~

After running ``pre-commit install --hook-type pre-commit --hook-type pre-push``:

- ``ruff-check`` lints and auto-fixes safe issues.
- ``ruff-format`` enforces consistent formatting.
- ``pyright-check`` runs ``uv run pyright`` on ``pre-commit``.
- ``pytest-check`` runs ``uv run pytest --no-cov`` on ``pre-push``.

Ruff also enforces the branch-complexity gate during ``ruff check``.

Run the checks manually with:

.. code-block:: bash

   uv run ruff check --fix .
   uv run ruff format .
   uv run pyright
   uv run radon cc src tests -s -a
   uv run pytest --no-cov

Or check without making changes:

.. code-block:: bash

   uv run ruff check .
   uv run ruff format --check .

Type Checking
~~~~~~~~~~~~~

``labapi`` uses `Pyright <https://github.com/microsoft/pyright>`_ for static
type checking.

.. code-block:: bash

   uv run pyright

Continuous Integration
~~~~~~~~~~~~~~~~~~~~~~

GitHub Actions split the main quality gates into separate workflows under
``.github/workflows``:

- unit tests
- lint
- format
- typecheck
- docs
- manual integration tests

Keeping these commands green locally is the fastest way to avoid CI surprises.

Type System
-----------

``labapi`` uses Python's type system as a first-class tool rather than optional
documentation. All new code should be fully type-annotated.

Key conventions:

- ``from __future__ import annotations`` is present in every module.
- Generics are used throughout the entry system so callers get concrete return
  types without extra casting.
- ``TYPE_CHECKING`` guards prevent circular imports while keeping type
  information available to static checkers.
- ``override`` is applied to method overrides so missing base methods are
  caught at check time.
- ``overload`` is used on ``__getitem__`` to express the different return
  types produced by different index kinds.

The project targets Python 3.10+ and uses modern typing features where they
improve clarity, with backports from ``typing_extensions`` where needed. Keep
source syntax compatible with Python 3.10; for example, prefer
``TypeVar``/``Generic`` over PEP 695 generic parameter syntax.

Related Pages
-------------

- :ref:`architecture` for the current internal module and cache model.
- :ref:`integration_design` for practical design guidance across the guide set.
- :ref:`reference` for generated API signatures while you are working.
