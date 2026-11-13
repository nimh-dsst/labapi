.. _json_entries:

JSON Entries
============

Use :meth:`~labapi.entry.collection.Entries.create_json_entry` to upload JSON
and add a rich-text preview to the same page.

How JSON Entries Are Stored
---------------------------

Creating a JSON entry creates two entries: an attachment holding the JSON, and
a rich-text entry showing a formatted copy on the page.

Create a JSON Entry
-------------------

For example:

.. code-block:: python

   from labapi import JsonData

   page = user.notebooks["My Notebook"].traverse("My Json Data/Page 1")

   my_data: JsonData = {
       "name": "Experiment 1",
       "date": "2024-01-01",
       "readings": [
           {"time": "10:00", "value": 1.23},
           {"time": "11:00", "value": 4.56},
       ],
       "completed": True,
   }

   attachment_entry, text_entry = page.entries.create_json_entry(my_data)

   print(f"Created attachment entry (ID: {attachment_entry.id})")
   print(f"Created text preview (ID: {text_entry.id})")

Any sequence or mapping is accepted, such as ``tuple``, ``range``, or
``MappingProxyType``, and is stored as a JSON array or object. ``bytes``,
``bytearray``, and ``memoryview`` values raise :class:`TypeError`; decode them
to ``str`` first.

Related Pages
-------------

- :ref:`entries` for entry types and entry creation methods.
- :doc:`/examples/json_sync` for a complete JSON sync workflow.
- :ref:`limitations` for caveats that apply to JSON entries.
