.. _api_calls:

Making Arbitrary API Calls
==========================

The methods on this page call LabArchives endpoints that ``labapi`` does not
wrap. The examples assume an authenticated ``user`` object; see
:ref:`first_calls` or :ref:`auth` to get one.

Choose a Call Path
------------------

.. list-table::
   :header-rows: 1

   * - Need
     - Use
     - Returns
   * - Signed request with ``uid`` added automatically
     - ``user.api_get()`` / ``user.api_post()``
     - Parsed XML as an ``lxml`` element
   * - Raw response headers and body
     - ``user.client.raw_api_get()`` / ``raw_api_post()``
     - :class:`requests.Response`
   * - Streaming large responses
     - ``user.client.stream_api_get()`` / ``stream_api_post()``
     - :class:`labapi.client.StreamingResponse`
   * - A signed URL for another tool
     - ``user.client.construct_url()``
     - A URL string

Use the User Object
-------------------

For XML endpoints, :meth:`~labapi.user.User.api_get` and
:meth:`~labapi.user.User.api_post` on :class:`~labapi.user.User` sign the
request and add your user ID (``uid``).

.. code-block:: python

   xml_response = user.api_get("notebooks/notebook_info", nbid="12345.6")
   print(xml_response.tag)

A non-2xx response raises :class:`~labapi.exceptions.AuthenticationError` or
:class:`~labapi.exceptions.ApiError`, and a request that gets no response
raises :class:`~labapi.exceptions.TransportError`; see :ref:`exceptions`. The
error message has the status code, the endpoint path, and the LabArchives
error code and description, but not the query string or the response body.

Parsing XML Responses
---------------------

XML responses are returned as ``lxml`` elements. Use the element directly, or
pull fields out of it with :func:`~labapi.util.extract.extract_etree`.

Using ``extract_etree``
~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from labapi.util import extract_etree, to_bool

   format_dict = {
       "notebook": {
           "name": str,
           "id": str,
           "is-student": to_bool,
           "signing": str,
       }
   }

   data = extract_etree(xml_response, format_dict)

   print(f"Notebook Name: {data['name']}")
   print(f"Is Student: {data['is-student']}")

By default a missing element, or a value a mapper rejects, raises
:class:`~labapi.exceptions.ExtractionError`. If a field is optional, pass
``raise_missing=False`` to leave it out of the result, and read it with
:meth:`dict.get`:

.. code-block:: python

   data = extract_etree(
       xml_response,
       {"caption": str, "attach-file-name": str},
       raise_missing=False,
   )

   filename = data.get("attach-file-name")

With ``raise_missing=False``, a value that is present but that the mapper
rejects is also omitted, with a :class:`RuntimeWarning`.

Raw and Streaming Responses
---------------------------

.. note::
   Every request times out after the ``timeout`` given to
   :class:`~labapi.client.Client`, in seconds (default 60), and then raises
   :class:`~labapi.exceptions.TransportError`. Raise it for long streaming
   downloads:

   .. code-block:: python

      client = Client(timeout=300)

Raw Responses
~~~~~~~~~~~~~

If you need HTTP headers or the raw response body, use
:meth:`~labapi.client.Client.raw_api_get` or
:meth:`~labapi.client.Client.raw_api_post`:

.. code-block:: python

   response = user.client.raw_api_get("users/max_file_size", uid=user.id)
   print(response.status_code)
   print(response.headers["Content-Type"])

Streaming Data
~~~~~~~~~~~~~~

For large attachments or incremental processing, use the streaming methods.
They return a :class:`~labapi.client.StreamingResponse`, which is both
iterable and a context manager:

.. code-block:: python

   with (
       user.client.stream_api_get(
           "entries/entry_attachment",
           uid=user.id,
           eid="987.6",
       ) as stream,
       open("large_file.zip", "wb") as f,
   ):
       for chunk in stream:
           f.write(chunk)

Constructing Signed URLs
------------------------

Use :meth:`~labapi.client.Client.construct_url` when code outside ``labapi``
needs to make the signed request, such as a browser download or another
service.

.. code-block:: python

   from datetime import timedelta

   url = user.client.construct_url(
       "entries/entry_attachment",
       query={"uid": user.id, "eid": "987.6"},
       expires_in=timedelta(minutes=10),
   )
   print(url)

Related Pages
-------------

- :ref:`auth`
- :ref:`first_calls`
- :ref:`reference` for the generated client and user API signatures.
