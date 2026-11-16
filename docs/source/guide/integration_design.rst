.. _integration_design:

Integration Design Guide
========================

Use these guidelines when designing long-running integrations.

Integration Cost Model
----------------------

Cheap Operations
~~~~~~~~~~~~~~~~

Reading fields or looking up IDs on objects and collections (``children``,
``entries``) you have already loaded makes no API calls.

Expensive Operations
~~~~~~~~~~~~~~~~~~~~

These operations make API calls:

- First access to lazy collections such as ``children`` and ``entries``.
- Calling ``refresh()`` and then reading the same objects again.
- Broad tree traversal or repeated full enumeration.
- Direct calls through ``user.api_get`` and ``user.api_post``.

Design Guidelines
-----------------

- Store LabArchives IDs in your integration's state. Use names and paths to
  find items and to display them.
- Limit traversal to the subtree and depth you need, and scan only what
  changed.
- Call ``refresh()`` before reads that must include changes made by another
  user, the web UI, or another API session.
- After ``refresh()``, fetch child objects again from the parent before reading
  their fields.
- After failures, look up the parent by stored ID, then re-read the child by
  ID.

Suggested Reading Order
-----------------------

1. :ref:`index_access` for duplicate-name and explicit lookup behavior.
2. :ref:`paths` for traversal and enumeration rules.
3. :ref:`clearing_cache` for cache invalidation and stale-reference behavior.
4. :ref:`api_calls` for making raw API requests.
