# Changelog

All notable changes to `labapi` are documented here in release order.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
This changelog is written for package users and maintainers, so entries call
out user-visible behavior, supported runtime changes, and release-engineering
details that affect development workflows.

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
