.. _writing_rich_text:

Writing Rich Text Entries
=========================

LabArchives rich-text entries use HTML for formatting. The examples below show
common markup patterns you can pass to :class:`~labapi.entry.entries.text.TextEntry`.

Create a Rich Text Entry
------------------------

The examples below assume you already have a ``page`` object:

.. code-block:: python

   from labapi import TextEntry

   page.entries.create(TextEntry, "<p>This is a rich text entry.</p>")

For a broader HTML reference, see the `MDN HTML elements reference <https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements>`_.

Common HTML Patterns
--------------------

Paragraphs
~~~~~~~~~~

Use ``<p>`` tags for basic paragraphs:

.. code-block:: html

   <p>This is a paragraph.</p>
   <p>This is another paragraph.</p>

Text Formatting
~~~~~~~~~~~~~~~

Use standard HTML tags for common inline formatting:

- Bold: ``<b>bold text</b>``
- Italic: ``<i>italic text</i>``
- Underline: ``<u>underlined text</u>``
- Strikethrough: ``<s>strikethrough text</s>``

Example:

.. code-block:: html

   <p>
       This paragraph contains <b>bold</b>,
       <i>italic</i>,
       <u>underlined</u>,
       and <s>strikethrough</s> text.
   </p>

Text Color
~~~~~~~~~~

Use the ``style`` attribute with the ``color`` property:

.. code-block:: html

   <p style="color:red;">This text is red.</p>
   <p style="color:#0000ff;">This text is blue.</p>

Tables
~~~~~~

Create tables with ``<table>``, ``<tr>``, ``<th>``, and ``<td>``:

.. code-block:: html

   <table border="1">
       <tr>
           <th>Header 1</th>
           <th>Header 2</th>
       </tr>
       <tr>
           <td>Row 1, Cell 1</td>
           <td>Row 1, Cell 2</td>
       </tr>
       <tr>
           <td>Row 2, Cell 1</td>
           <td>Row 2, Cell 2</td>
       </tr>
   </table>

Lists
~~~~~

Use ``<ul>`` or ``<ol>`` with ``<li>`` items:

.. code-block:: html

   <ul>
       <li>Item 1</li>
       <li>Item 2</li>
       <li>Item 3</li>
   </ul>

.. code-block:: html

   <ol>
       <li>First item</li>
       <li>Second item</li>
       <li>Third item</li>
   </ol>

Related Pages
-------------

- :ref:`entries` for entry type behavior and update semantics.
- :doc:`/examples/csv_table` for a complete CSV-to-HTML workflow.
- :ref:`creating_pages` for creating a page before adding rich-text entries.
