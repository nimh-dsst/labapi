# Test Plan

## Goals

- Make test intent obvious from the harness being used.
- Keep case setup local so multi-case tests are easy to write.
- Stop mixing pure unit tests, request/response protocol tests, stateful mock-backend tests, and live integration tests in the same style.
- Use the new mock harness to remove repetitive XML and response wiring, without forcing every test through one big seeded world.

## Design Principles

- Prefer the shallowest harness that can express the behavior under test.
- Keep scenario state small and explicit inside each test unless the same setup is reused heavily.
- Treat canonical record renderers as valid payload builders, not as the only way to express cases.
- Use `XmlApi` for odd-but-valid XML payloads.
- Use raw bytes only for truly malformed XML at the API boundary.
- Do not rebuild large coherent notebook trees unless the test actually needs tree behavior.

## Test Tiers

### 1. Pure Unit Tests

Use direct object construction, `Mock`, and simple value fixtures.

Best for:

- collection semantics
- local object properties
- copy/iteration behavior
- validation logic
- utility functions

Avoid:

- queued XML responses
- mock backend state

Current examples:

- `tests/util/*`
- `tests/entry/entries/*`
- large parts of `tests/tree/test_page.py`
- large parts of `tests/test_client.py`

### 2. Protocol Tests

Use the queue-driven `client` fixture plus `xml`.

Best for:

- request shape assertions
- response parsing
- auth/signing edge cases
- malformed or partial API payload handling
- single-call client and model behavior

Authoring rules:

- Use small helper builders for canonical valid responses when they make the case clearer.
- Use `XmlApi` directly when fields must be omitted, duplicated, reordered, or otherwise made unusual.
- Use raw byte payloads for parser failure cases.
- Keep request assertions close to the behavior being tested.

This tier should absorb most tests that currently depend on the old `api_response` / helper-builder style.

### 3. Stateful Mock-Backend Tests

Use `backend` or `backend_client`.

Best for:

- multi-call workflows
- create-then-fetch behavior
- update flows
- attachment round-trips
- tree mutations
- notebook/page/entry interactions across multiple API calls

Authoring rules:

- Build only the records needed for the case.
- Prefer tiny local setup over a global seeded notebook tree.
- Add small helper functions only for genuinely repeated setup fragments.
- Keep backend state setup explicit in the test when the variation matters.

This tier should replace the old large reusable object-graph fixtures for most behavior tests.

### 4. Live Integration Tests

Keep behind `@pytest.mark.integration` and `--integration`.

Best for:

- verifying assumptions against real LabArchives behavior
- auth and environment-dependent flows
- backend mock fidelity checks for especially risky endpoints

These should stay narrow and intentionally fewer than the mock-backed tests.

## Revised Fixture Surface

The revised suite should center on four fixtures:

- `xml`: low-level XML builder for response authoring
- `client`: queued protocol-style mock client
- `backend`: explicit stateful LabArchives backend
- `backend_client`: real `LA.Client` wired to the backend shim

The old large domain fixtures should not be carried over wholesale. If a repeated pattern emerges, add a small focused helper instead of a global seeded world.

Good future helpers:

- request echo helpers for repeated `<request>` children
- tiny record builders for common notebook/page/entry fragments
- narrow backend setup helpers such as `make_page(...)` or `add_attachment(...)`

Avoid:

- one fixture that seeds an entire notebook tree for broad reuse
- helpers that hide which records exist in the case
- record renderers with endpoint-view flags

## Proposed Suite Structure

The suite should be reorganized by test style first, then by domain.

Suggested shape:

- `tests/unit/`
- `tests/protocol/`
- `tests/backend/`
- `tests/integration/`

Within those:

- `client/`
- `user/`
- `tree/`
- `entry/`
- `util/`
- `examples/` where still useful

If a full directory move is too noisy, the same separation can be applied incrementally inside the current tree by renaming modules and grouping them by style over time.

## Migration Plan

### Phase 1: Activate the New Harness

- Make the new fixture facade the active `conftest` path, or import it from the active root `conftest.py`.
- Keep live integration marker handling from `tests/conftest.py`.
- Do not attempt a drop-in compatibility layer for the old test DSL.

### Phase 2: Move Protocol Tests First

Prioritize modules that mostly assert request shape and XML parsing:

- `tests/test_client.py`
- `tests/test_user.py`
- parsing-focused parts of `tests/entry/test_collection.py`
- parsing-focused parts of `tests/tree/*`

Target outcome:

- tests use `client` + `xml`
- payload authorship is explicit
- malformed payload cases are clearer

### Phase 3: Move Stateful Workflow Tests

Convert tests that currently rely on larger reusable object worlds into backend-backed workflow tests:

- tree mutation flows
- page entry loading
- attachment create/update/fetch flows
- user/notebook/page traversal flows

Target outcome:

- workflows are expressed through `backend` / `backend_client`
- each test sets up only the records it needs
- fewer broad fixtures with hidden coupling

### Phase 4: Split by Style

Once enough modules are converted:

- separate pure unit, protocol, backend, and live integration tests physically
- remove remaining old response helper DSL where it no longer earns its keep
- keep only helpers that still reduce real repetition

## Module Priorities

### High Priority

- `tests/test_client.py`
- `tests/test_user.py`
- `tests/entry/test_collection.py`
- `tests/tree/test_page.py`
- `tests/tree/test_mixins.py`

These have the most overlap with the new harness and the most value from cleaner separation of test styles.

### Medium Priority

- `tests/tree/test_directory.py`
- `tests/tree/test_notebook.py`
- `tests/tree/test_collection.py`
- `tests/entry/test_attachment.py`

### Lower Priority

- `tests/util/*`
- `tests/examples/*`
- existing live integration tests

These either already read clearly, depend less on the harness, or should move only after the core tiers are settled.

## Exit Criteria

The revised suite is in a good state when:

- a reader can tell the style of a test from the fixture/harness immediately
- malformed payload tests are isolated to protocol tests
- multi-step behavior tests use backend state instead of queued XML gymnastics
- pure unit tests do not depend on API-shaped fixtures
- broad seeded fixtures are no longer carrying unrelated cases
- live integration coverage is narrow and intentional

## Non-Goals

- perfect one-to-one migration from the old fixtures
- one universal fixture world for all tests
- abstracting away every XML detail
- hiding endpoint-specific behavior behind generic record flags
