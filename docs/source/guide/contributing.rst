.. _contributing:

Contributing
============

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

Unit tests use a ``MockClient`` with synthetic XML responses constructed from
the LabArchives API documentation, and run offline.

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

``ruff check`` also enforces a branch-complexity limit.

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

GitHub Actions runs these as separate workflows under ``.github/workflows``:

- unit tests
- lint
- format
- typecheck
- docs
- manual integration tests

Type System
-----------

All new code should be fully type-annotated.

Key conventions:

- ``from __future__ import annotations`` is used in modules that rely on
  forward references.
- Generics are used throughout the entry system so callers get concrete return
  types without extra casting.
- Imports that would be circular go under a ``TYPE_CHECKING`` guard.
- Method overrides are marked with ``override``.
- ``overload`` is used on ``__getitem__`` to express the different return
  types produced by different index kinds.

The project targets Python 3.11+; use typing features supported by Python 3.11
or available from ``typing_extensions``. Keep
source syntax compatible with Python 3.11; for example, prefer
``TypeVar``/``Generic`` over PEP 695 generic parameter syntax.

Related Pages
-------------

- :ref:`architecture` for the current internal module and cache model.
- :ref:`integration_design` for integration design guidance.
- :ref:`reference` for generated API signatures.
