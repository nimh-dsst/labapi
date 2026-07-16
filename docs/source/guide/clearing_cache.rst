.. _clearing_cache:

Clearing Cache
==============

The LabArchives API client caches child-node lists and page-entry collections so repeated reads
do not issue API calls. Call ``refresh()`` before reading changes made outside the current
session.

Refreshing Tree and Entry Caches
--------------------------------

Tree nodes (notebooks, directories, and pages) provide a :meth:`~labapi.tree.mixins.AbstractBaseTreeNode.refresh`
method that clears cached children for containers or cached entries for pages, so the next
property access fetches them again.

Refreshing a Page
~~~~~~~~~~~~~~~~~

When you refresh a page, the cached entries are cleared:

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

For directories and notebooks, ``refresh()`` clears cached children:

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

Create, rename, move, and delete operations update the in-memory tree after the API call succeeds, so ``refresh()`` is not needed to see that operation's local result.

This includes:

* ``create()`` appending a new page or directory to the parent container
* ``node.name = "..."`` updating the current object's name in memory after the API call
* ``move_to()`` updating the node's parent and both containers' child lists
* ``delete()`` renaming and moving the current node into ``API Deleted Items``

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
    ``refresh()`` does not update existing child-object references:

    **Stale object references**: Existing references to child pages, directories, or entries are
    not replaced by ``refresh()`` and can keep stale cached data.

    **Example: stale entry reference**

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

The following data is cached and will be cleared by ``refresh()``:

**For notebooks and directories:**

* List of child pages and subdirectories
* Child count

**For pages:**

* List of entries on the page
* Entry content and metadata

**Not cleared by refresh():**

* User authentication state
* The :class:`~labapi.user.User` ``notebooks`` collection, which is built once at
  login and is not affected by tree or page ``refresh()``

Related Pages
-------------

* :ref:`paths` for mutation and traversal workflows where stale caches are common.
* :ref:`navigating` for descendant enumeration examples that interact with cached tree state.
* :doc:`/examples/json_sync` for synchronization workflows that may require periodic refreshes.
* :ref:`limitations`
