.. _integration_design:

Integration Design Guide
========================

Use these guidelines when designing long-running integrations.

Integration Cost Model
----------------------

Cheap Operations
~~~~~~~~~~~~~~~~

These operations use already-loaded local state:

- Reading fields on objects you already loaded.
- Reusing materialized ``children`` and ``entries`` collections.
- Matching IDs inside collections you already fetched.

Expensive Operations
~~~~~~~~~~~~~~~~~~~~

These operations issue API calls or can cause many API calls:

- First access to lazy collections such as ``children`` and ``entries``.
- Calling ``refresh()`` and then reading the same objects again.
- Broad tree traversal or repeated full enumeration.
- Explicit low-level calls through ``user.api_get`` and ``user.api_post``.

Design Guidelines
-----------------

- Store LabArchives IDs as the primary references in integration state. Names
  and paths are best treated as discovery and presentation data.
- Keep traversal bounded by scope and depth, and favor incremental scans over
  full rescans.
- Place ``refresh()`` before reads that must include changes made by another
  user, the web UI, or another API session.
- After ``refresh()``, reacquire child objects from the refreshed parent before
  reading child fields.
- After failures, look up the parent by stored ID, then re-read the child by
  ID.

Suggested Reading Order
-----------------------

1. :ref:`index_access` for duplicate-name and explicit lookup behavior.
2. :ref:`paths` for traversal and enumeration rules.
3. :ref:`clearing_cache` for cache invalidation and stale-reference behavior.
4. :ref:`api_calls` for low-level request access patterns.
