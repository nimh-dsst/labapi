.. _notebook_exports:

Notebook Backups and Exports
============================

Use :meth:`~labapi.tree.notebook.Notebook.backup` to save the native
LabArchives response, or :meth:`~labapi.tree.notebook.Notebook.export` to
write a readable directory tree. The examples below assume you already have a
``notebook`` object.

Download a Native Backup
------------------------

Write LabArchives' native backup archive to a local file:

.. code-block:: python

   notebook.backup("my_notebook.7z")

To omit attachment payloads from the archive, pass
``include_attachments=False``:

.. code-block:: python

   notebook.backup("metadata_only.7z", include_attachments=False)

LabArchives only permits the notebook owner's authenticated account to request
a native backup. Error code ``4547`` means the currently authenticated account
is not the owner; check ``Notebook Settings > Users`` in the LabArchives web UI
and retry with the owner's credentials.

Export a Directory Tree
-----------------------

Export the notebook's top-level directories and pages to a local destination:

.. code-block:: python

   notebook.export("my_notebook")

The destination contains numeric ordering prefixes, page content files, and a
``.labarchives.json`` manifest for every page. The manifest records the page
and entry IDs, output filenames, entry types, and available attachment details.
For example:

.. code-block:: text

   my_notebook/
   └── 1_Experiments/
       └── 1_Run 1/
           ├── 1_text.html
           ├── 2_results.csv
           └── .labarchives.json

Empty directories are created, and empty pages still receive their manifest.
If the destination already exists and is not empty,
:meth:`~labapi.tree.notebook.Notebook.export` raises :class:`FileExistsError`.
Pass ``overwrite=True`` to replace it.

Choose an Export Source
-----------------------

``source="auto"`` is the default. It uses a native backup archive when
available and otherwise walks the live API tree. To read native archives,
install the ``export`` extra:

.. code-block:: bash

   pip install "labapi[export]"

Use ``source="backup"`` to require the native archive, or ``source="walk"``
to bypass it and read the live tree directly. A live walk can take a long time
for large notebooks: LabArchives requires many API requests to enumerate and
download page content and attachment files, so duration grows with notebook
size.

Related Pages
-------------

- :ref:`installation` for optional dependency installation.
- :ref:`limitations` for known API and entry-type constraints.
