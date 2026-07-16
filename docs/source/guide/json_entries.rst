.. _json_entries:

JSON Entries
============

Use :meth:`~labapi.entry.collection.Entries.create_json_entry` to upload JSON
and add a rich-text preview to the same page.

How JSON Entries Are Stored
---------------------------

When you create a JSON entry with ``labapi``, the library creates two related
entries:

- A JSON attachment that stores the JSON-serialized data.
- A rich-text preview entry that shows a formatted, human-readable version in
  the notebook page.

Create a JSON Entry
-------------------

Use :meth:`~labapi.entry.collection.Entries.create_json_entry` on
``page.entries``:

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

Related Pages
-------------

- :ref:`entries` for entry types and entry creation methods.
- :doc:`/examples/json_sync` for a complete JSON sync workflow.
- :ref:`limitations` for caveats that apply to JSON entries.
