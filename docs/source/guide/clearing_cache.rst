.. _clearing_cache:

Clearing Cache
==============

``labapi`` caches each container's children and each page's entries, so repeated reads make no
API calls.

Refreshing Tree and Entry Caches
--------------------------------

Tree nodes (notebooks, directories, and pages) provide a :meth:`~labapi.tree.mixins.AbstractBaseTreeNode.refresh`
method that clears cached children for containers or cached entries for pages, so the next
property access fetches them again.

Refreshing a Page
~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Get a page
    page = notebook.traverse("My Folder/My Page")

    # Work with entries
    entries = page.entries  # Fetches from API and caches

    # Some time later, you want to see if new entries were added
    page.refresh()

    # Next access will fetch fresh data from the API
    entries = page.entries  # Re-fetches from API

Refreshing a Directory or Notebook
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Get a directory
    directory = notebook.traverse("My Folder")

    # Access children
    children = directory.children  # Fetches and caches

    # Refresh to see if new pages/subdirectories were added
    directory.refresh()

    # Next access gets fresh data
    children = directory.children  # Re-fetches from API

When Local Mutations Do Not Need Refresh
----------------------------------------

Create, rename, move, and delete update the in-memory tree once the API call succeeds, so you do not need ``refresh()`` afterwards.

``create()`` appends the new page or directory to its parent, and ``node.name = "..."`` renames
the object in memory. ``move_to()`` updates the node's parent and both containers' child lists,
and ``delete()`` renames the node and moves it into ``API Deleted Items``.

.. code-block:: python

    from labapi import NotebookDirectory, NotebookPage

    archive = notebook.create(NotebookDirectory, "Archive")
    page = notebook.create(NotebookPage, "Fresh Results")

    print("Fresh Results" in list(notebook))

    page.move_to(archive)
    print(page.parent is archive)  # True without refresh()

When to Refresh Data
--------------------

Use ``refresh()`` when you need to pick up changes made by another user, the LabArchives web UI, or another API session.

Example: Polling for New Entries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import time

    page = notebook.traverse("Experiment Results")

    while True:
        # Clear cache and check for new entries
        page.refresh()
        entries = page.entries

        print(f"Current entry count: {len(entries)}")

        if len(entries) >= 10:
            print("Required entries found!")
            break

        time.sleep(30)  # Wait 30 seconds before checking again

Limitations
-----------

.. warning::
    ``refresh()`` does not update child pages, directories, or entries that you already hold,
    so they can keep stale data:

    .. code-block:: python

        page = notebook.traverse("My Page")
        entry = page.entries[0]  # Get reference to first entry

        # Refresh the page
        page.refresh()

        # This entry object still has old cached data!
        # It wasn't invalidated by the refresh
        print(entry.content)  # May show stale data

    After ``refresh()``, re-fetch child objects before reading them:

    .. code-block:: python

        page = notebook.traverse("My Page")

        # Refresh and re-fetch entries
        page.refresh()
        entry = page.entries[0]  # Get a fresh reference

        print(entry.content)  # Shows current data

What Gets Cached
----------------

On a notebook or directory, ``refresh()`` clears the list of child pages and subdirectories
and the child count. On a page, it clears the list of entries and their content and metadata.

**Not cleared by refresh():**

* The :class:`~labapi.user.User` ``notebooks`` collection, which is built once at
  login

Related Pages
-------------

* :ref:`paths`
* :ref:`navigating`
* :doc:`/examples/json_sync`
* :ref:`limitations`
