# Changelog

All notable changes to `labapi` are documented here in release order.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
This changelog is written for package users and maintainers, so entries call
out user-visible behavior, supported runtime changes, and release-engineering
details that affect development workflows.

## 1.2.0 - Unreleased

### Added

- Entries now expose optional read-only creation, update, and version metadata.
- `Client` request methods accept a `timeout` parameter.
- `Notebook.backup()` downloads a notebook's native LabArchives backup archive
  or JSON response, with options to omit attachment payloads.
- `Notebook.export()` materializes a notebook as a local directory tree,
  preserving empty directories and pages, entry ordering, attachments, and
  per-page metadata. The optional `labapi[export]` extra reads native backup
  archives; the default source falls back to the live API when needed.

### Changed

- Client base URLs now discard fragments and warn when they contain query
  parameters that cannot be preserved in API requests.
- Versioned documentation shows only the newest release candidate and keeps
  the root and `latest/` aliases on the newest final release.

### Fixed

- Authentication honors configured timeouts and token expiry, and
  `LA_AUTH_BROWSER=edge` reliably selects Microsoft Edge.
- Tree traversal correctly handles escaped names, membership checks with
  `Index.Name`, notebook-path hashing, and relative paths rooted at a notebook.
- Attachment uploads rewind seekable files when needed; cached attachment
  downloads stream in chunks; and attachment updates report LabArchives error
  4999 with actionable context.
- `json_sync` preserves JSON attachments with duplicate basenames and records
  failures for individual attachment downloads instead of abandoning the entry.
- `create_json_entry()` raises `PartialEntryCreateError` when an attachment is
  orphaned, and unsupported entry wrappers are rejected before creation.
- XML responses retain their original encoding, `EntrySearch` tolerates
  disappearing result pages, and extraction errors handle mappers without a
  `__name__` attribute.
- `PlainTextEntry.content` rejects non-string values before an API request,
  the public parse exceptions are available from `labapi`, and the API
  Deleted Items directory cannot be deleted accidentally.
- The model-logging example escapes metadata and uses an ASCII-safe success
  message.

### Security

- `ApiError` masks sensitive URL query parameters in its messages and
  tracebacks.
- The built-in authentication callback uses an unguessable loopback path and
  a plain-text response.

## 1.1.1 - 2026-07-05

### Fixed

- Fixed README documentation links that returned 404 by publishing a stable
  `latest/` docs alias alongside the versioned directories.
- Corrected documentation errors: the `enumerate_all()` depth example,
  `create(parents=False)` raising `ValueError` for any multi-segment path, the
  exception hierarchy (`PathError`, `ExtractionError`, `TreeChildParseError`),
  `User.notebooks` caching, the scope of `strict_cert=False` (relaxes strict
  X.509 validation only, not certificate verification), the folder-download
  output layout diagram, and `UnknownEntry` vs `UnimplementedEntry` wrapping.

### Changed

- Expanded documentation: full `Notebook.search()` coverage (lazy
  `EntrySearch`, zero-based `page()` access, result-page metadata) and a new
  "Obtain API Keys" section.
- Copy-edited the documentation and public docstrings for precision and
  concision.

### Security

- Raised the minimum `cryptography` requirement to 48.0.1 and updated the
  locked version, dropping wheels that bundle a vulnerable OpenSSL
  (Dependabot alert 15).

## 1.1.0 - 2026-06-02

### Added

- `Attachment.from_file()` now accepts filesystem `str` or `Path` objects in
  addition to file-like objects.
- `Notebook.search()` for paginated LabArchives entry search results using
  normal entry objects.
- Support for escaped separators (`\/`) in notebook paths, enabling access to
  and creation of notebook nodes with literal slashes in their names.
- Official support for Python 3.10 and 3.11.
- `typing-extensions` as a runtime dependency so code can use backported typing
  helpers such as `Self`, `override`, and `Buffer` while supporting Python 3.10.
- Lazy environment-variable loading through `labapi.util.env.getenv()`. When
  `python-dotenv` is installed, `.env` is loaded on first credential lookup
  instead of during `labapi.client` import.

### Changed

- Refactored the `json_sync` example into a reusable utility with
  comprehensive tests.
- Rewrote the `csv_table` example for improved clarity and usability.
- Refactored the `folder_download` example into clearer reusable download
  logic.
- Reworked entry factory fallback handling. Unknown upstream LabArchives part
  types now load as `UnknownEntry`, while recognized but unimplemented part
  types load as `UnimplementedEntry`; both still reject unsupported updates.
- Updated attachment cloning to use an explicit random-access capability check
  instead of requiring every file-like object to expose a reliable
  `seekable()` method.
- Kept spooled attachment buffers open after `Attachment.from_file()` returns,
  while still preserving the caller's original file cursor position.

### Fixed

- Fixed runtime typing in `Attachment.from_file()` to support both file-like
  and path-like inputs correctly.
- Improved `Attachment.from_file()` support for random-access binary streams
  that do not expose `seekable()`.
- Fixed relative path resolution bugs when using the `/` operator with absolute
  and relative `NotebookPath` objects.

## 1.0.3 - 2026-04-15

### Changed

- Refined the client auth flow and browser detection behavior.
- Simplified tree path handling.
- Switched the `1.0` type-check workflow from `mypy` to `ty`.
- Refreshed package metadata, README content, and Zenodo configuration.
- Updated `pillow` and `pytest`.

### Fixed

- Restored datetime-based URL signing support.
- Improved browser detection robustness when detectable values arrive with
  incorrect types.
- Fixed test compatibility issues in the `1.0` maintenance branch.
- Reduced tree creation complexity in the `v1.0.3` stabilization pass.

## 1.0.2 - 2026-04-10

### Changed

- Cleaned up the PyPI README and related package metadata.

## 1.0.1 - 2026-04-10

### Added

- Initial TestPyPI publishing workflow.
- GitHub issue templates.
- Reusable GitHub Actions checks and broader local tooling support.

### Changed

- Improved versioning and generated documentation metadata.
- Refreshed contributor and Sphinx configuration docs.
- Updated `cryptography`, `pygments`, and `requests`.

## 1.0.0 - 2026-04-01

### Added

- Initial stable release of `labapi`.
- Support for LabArchives authentication, notebook tree traversal, and
  page and entry operations from Python.
- Project documentation and example workflows for common notebook automation
  tasks.
