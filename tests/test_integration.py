"""Integration tests covering end-to-end LabArchives workflows."""

import json
import os
from collections.abc import Iterator
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import pytest

import labapi as LA
from labapi import Index

pytestmark = pytest.mark.integration

try:
    from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

    load_dotenv()
except ImportError:
    pass


@pytest.fixture(scope="session")
def la_client() -> Iterator[LA.Client]:
    """Initialize a LabArchives API client from environment variables."""
    if (
        not os.getenv("ACCESS_KEYID")
        or not os.getenv("ACCESS_PWD")
        or not os.getenv("API_URL")
    ):
        pytest.fail("--integration requires ACCESS_KEYID, ACCESS_PWD, and API_URL.")
    with LA.Client() as client:
        yield client


@pytest.fixture(scope="session")
def la_user(la_client: LA.Client) -> LA.User:
    """Authenticate a LabArchives user for integration tests."""
    interactive = os.getenv("AUTH_INTERACTIVE", "false").lower() == "true"

    if interactive:
        return la_client.default_authenticate()

    email = os.getenv("AUTH_EMAIL")
    key = os.getenv("AUTH_KEY")
    if not email or not key:
        pytest.fail(
            "--integration requires AUTH_EMAIL and AUTH_KEY for non-interactive login."
        )

    return la_client.login(email, key)


@pytest.fixture(scope="session")
def test_notebook(la_user: LA.User):
    """Opens the specific notebook for testing."""
    nb_name = os.getenv("NOTEBOOK", "My Test Notebook")
    # Search by name slice
    notebooks = la_user.notebooks[Index.Name : nb_name]
    if not notebooks:
        pytest.fail(f"Notebook '{nb_name}' not found.")
    return notebooks[0]


def get_or_create_dir(
    parent: LA.Notebook | LA.NotebookDirectory, name: str
) -> LA.NotebookDirectory:
    """Get or create a directory by name."""
    return parent.dir(name)


@pytest.fixture(scope="session")
def root_test_dir(test_notebook: LA.Notebook):
    """Return the root integration-test directory."""
    return get_or_create_dir(test_notebook, "LabArchives API Test")


@pytest.fixture(scope="session")
def tests_dir(root_test_dir: LA.NotebookDirectory):
    """Returns the 'tests' subdirectory."""
    return get_or_create_dir(root_test_dir, "tests")


def add_readme(workspace: LA.NotebookDirectory, scenario: str, actions: str):
    """Add the required README page to a test workspace."""
    readme_page = workspace.page("README")
    content = f"SCENARIO: {scenario}\n\nACTIONS TAKEN:\n{actions}"
    readme_page.entries.create(LA.PlainTextEntry, content)


def get_or_create_page_with_json(
    parent: LA.NotebookDirectory, name: str, data: dict
) -> LA.NotebookPage:
    """Get or create a page and ensure it has the JSON entry pair."""
    new_page = parent.page(name)
    if len(new_page.entries):
        return new_page
    # create_json_entry returns (AttachmentEntry, TextEntry)
    new_page.entries.create_json_entry(data)
    return new_page


@pytest.fixture(scope="session")
def data_dir_structure(root_test_dir: LA.NotebookDirectory):
    """Build and return the shared integration-test data tree."""
    data_dir = get_or_create_dir(root_test_dir, "data")
    m1_dir = get_or_create_dir(data_dir, "method_1")

    # 1. method_1/meta.json using the new dual-entry system
    get_or_create_page_with_json(m1_dir, "meta.json", {"name": "", "description": ""})

    subjects_dir = get_or_create_dir(m1_dir, "subjects")

    for i in range(1, 4):
        subj_name = f"subj_{i}"
        s_dir = get_or_create_dir(subjects_dir, subj_name)

        # Subject meta.json using the new system
        gender = "male" if i % 2 == 0 else "female"
        get_or_create_page_with_json(
            s_dir, "meta.json", {"id": f"test subject {i} id", "gender": gender}
        )

        sess_root = get_or_create_dir(s_dir, "sessions")
        sess_1 = get_or_create_dir(sess_root, "1")

        # data.json (Raw experimental data remains a standard attachment)
        if not sess_1[Index.Name : "data.json"]:
            source_attachment = LA.Attachment.from_file(
                Path(__file__).parent / "test_entry.json"
            )
            try:
                sess_1.create(LA.NotebookPage, "data.json").entries.create(
                    LA.AttachmentEntry, source_attachment
                )
            finally:
                source_attachment.close()

        # notes.txt
        if not sess_1[Index.Name : "notes.txt"]:
            n_page = sess_1.create(LA.NotebookPage, "notes.txt")
            n_page.entries.create(
                LA.AttachmentEntry,
                LA.Attachment(BytesIO(b""), "text/plain", "notes.txt", "Notes"),
            )

    return data_dir


@pytest.fixture
def test_env(
    request: pytest.FixtureRequest,
    tests_dir: LA.NotebookDirectory,
    data_dir_structure: LA.NotebookDirectory,
):
    """Create an isolated timestamped workspace for the current test."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    test_folder_name = f"test: {request.node.name} {timestamp}"  # pyright: ignore[reportUnknownMemberType]

    # Create the isolated workspace
    workspace = tests_dir.create(LA.NotebookDirectory, test_folder_name)

    # Copy the baseline data structure into this workspace
    # Note: Using your MixinTreeCopy logic
    data_dir_structure.copy_to(workspace)

    return workspace.refresh()


def test_add_session_notes(test_env):
    """Scenario: Adding clinician notes to an existing session file."""
    # Setup README
    add_readme(
        test_env,
        "Add new session notes",
        "Added a comment to notes.txt for subject 1 session 1.",
    )

    # Navigate to Subj 1 -> Sessions -> 1 -> notes.txt
    # We navigate through the copy in our test_env
    notes_page = test_env.traverse(
        "data/method_1/subjects/subj_1/sessions/1/notes.txt"
    ).as_page()

    # Add the plain text entry
    note = notes_page.entries.create(LA.PlainTextEntry, "fell asleep during test")

    notes_page = (
        test_env.refresh()
        .traverse("data/method_1/subjects/subj_1/sessions/1/notes.txt")
        .as_page()
    )
    assert notes_page.entries[note.id].content == "fell asleep during test"


def test_move_and_merge_sessions(test_env):
    """Scenario: Transferring a session from one subject to another."""
    add_readme(
        test_env,
        "Move subject 2's session 1 to subject 1",
        "Renamed S2-S1 to '2', moved to S1, and verified placement.",
    )

    s1_sessions = test_env.traverse("data/method_1/subjects/subj_1/sessions").as_dir()
    s2_sessions = test_env.traverse("data/method_1/subjects/subj_2/sessions").as_dir()

    # 1. Get Session 1 from Subject 2
    session_to_move = s2_sessions[Index.Name : "1"][0]
    moved_session_id = session_to_move.id

    # 2. Rename it to '2' to avoid collision in the destination
    session_to_move.name = "2"

    # 3. Move it to Subject 1's session directory
    session_to_move.move_to(s1_sessions)

    # Verify move
    s1_sessions.refresh()
    s2_sessions.refresh()
    assert s1_sessions[Index.Id : moved_session_id].name == "2"
    assert len(s2_sessions[Index.Name : "1"]) == 0


def test_upload_new_session(test_env):
    """Scenario: Creating a second session for a subject."""
    add_readme(
        test_env,
        "Upload a new session",
        "Created 'session 2' in subject 2 with empty notes.",
    )

    sess_root = test_env.traverse("data/method_1/subjects/subj_2/sessions").as_dir()

    # Create session 2
    sess_2 = sess_root.create(LA.NotebookDirectory, "2")
    notes_page = sess_2.create(LA.NotebookPage, "notes.txt")
    note = notes_page.entries.create(LA.PlainTextEntry, "New session started.")

    refreshed_session = sess_root.refresh()[Index.Id : sess_2.id].as_dir()
    refreshed_notes = refreshed_session[Index.Id : notes_page.id].as_page()
    assert refreshed_notes.entries[note.id].content == "New session started."


def test_fix_metadata(test_env):
    """Scenario: Correcting metadata by updating both the raw JSON and the rich text preview."""
    add_readme(
        test_env,
        "Fix data",
        "Corrected gender field in Subject 1's meta.json by updating both entries in-place.",
    )

    meta_page = test_env.traverse("data/method_1/subjects/subj_1/meta.json").as_page()

    # Identify the two parts of the JSON entry
    rich_text_entry = None
    attachment_entry = None

    for entry in meta_page.entries:
        if isinstance(entry, LA.TextEntry):
            rich_text_entry = entry
        elif isinstance(entry, LA.AttachmentEntry):
            attachment_entry = entry

    if not rich_text_entry or not attachment_entry:
        pytest.fail("Dual JSON entries (Attachment + Text) not found on page.")
    assert rich_text_entry is not None
    assert attachment_entry is not None
    rich_text_entry_id = rich_text_entry.id
    attachment_entry_id = attachment_entry.id

    # 1. Prepare new data
    new_data = {"id": "test subject 1 id", "gender": "male"}
    new_json_bytes = json.dumps(new_data).encode("utf-8")

    # 2. Update the Raw Attachment in-place
    # We create a new Attachment object to pass to the setter
    existing_attachment = attachment_entry.content
    try:
        existing_filename = existing_attachment.filename
    finally:
        existing_attachment.close()
    new_file_content = LA.Attachment(
        backing=BytesIO(new_json_bytes),
        mime_type="application/json",
        filename=existing_filename,  # Keep existing filename
        caption="Updated metadata file via API",
    )
    try:
        attachment_entry.content = new_file_content
    finally:
        new_file_content.close()

    # 3. Update the Rich Text Preview in-place
    # We reuse the formatting logic from create_json_entry
    rich_text_entry.content = f"""
<p>Reference Attachment: {existing_filename}</p>
<p>Entry ID: {attachment_entry.id}</p>
<pre>
{json.dumps(new_data, indent=4)}
</pre>
"""

    # Verification
    # Check rich text
    assert "male" in rich_text_entry.content
    # Check raw attachment content
    updated_attachment = attachment_entry.content
    try:
        assert b"male" in updated_attachment.read()
    finally:
        updated_attachment.close()

    refreshed_meta = (
        test_env.refresh().traverse("data/method_1/subjects/subj_1/meta.json").as_page()
    )
    refreshed_text = refreshed_meta.entries[rich_text_entry_id]
    assert isinstance(refreshed_text, LA.TextEntry)
    assert "male" in refreshed_text.content
    refreshed_attachment_entry = refreshed_meta.entries[attachment_entry_id]
    assert isinstance(refreshed_attachment_entry, LA.AttachmentEntry)
    refreshed_attachment = refreshed_attachment_entry.content
    try:
        assert json.load(refreshed_attachment) == new_data
    finally:
        refreshed_attachment.close()


def test_delete_subject(test_env):
    """Scenario: Deleting a subject from the dataset."""
    add_readme(
        test_env,
        "Delete subject 3",
        "Renamed and moved Subject 3 to the 'API Deleted Items' directory.",
    )

    # 1. Navigate to Subject 3 within the isolated test environment
    subjects_dir = test_env.traverse("data/method_1/subjects").as_dir()

    # Ensure subject 3 exists before deletion
    subj3_list = subjects_dir[Index.Name : "subj_3"]
    if not subj3_list:
        pytest.fail("Subject 3 not found in the test workspace.")

    subj3 = subj3_list[0]
    assert isinstance(subj3, LA.NotebookDirectory)
    deleted_subject_id = subj3.id

    # 2. Execute the deletion
    # This triggers the client logic:
    # - Renames to "subj_3 - Deleted at YYYY-MM-DD..."
    # - Moves to root/"API Deleted Items"
    subj3.delete()

    # 3. Verification
    # Subject 3 should no longer be in the subjects directory
    subjects_dir.refresh()
    assert len(subjects_dir[Index.Name : "subj_3"]) == 0

    # Verify it exists in the 'API Deleted Items' folder at the notebook root
    # Note: delete() moves it to self._root (the Notebook)
    deleted_items_dir = test_env.root.refresh().traverse("API Deleted Items").as_dir()

    deleted_subject = deleted_items_dir[Index.Id : deleted_subject_id]
    assert deleted_subject.name.startswith("subj_3 - Deleted at")


def test_paper_qc_workflow(test_env: LA.NotebookDirectory, tmp_path: Path) -> None:
    """Exercise the path, JSON-entry, refresh, and attachment workflow from the paper."""
    add_readme(
        test_env,
        "Run the paper's cohort QC workflow",
        "Created subject JSON records and a dashboard with summary data and a figure.",
    )
    qc = test_env.dir("Partly Cloudy QC")
    subjects = ("sub-alpha", "sub-beta", "sub-gamma")

    for subject in subjects:
        page = qc.page(subject)
        page.entries.create_json_entry(
            {"subject": subject, "group": "partly cloudy", "mean_dvars": 1.25},
            filename=f"{subject}.json",
        )

    qc = test_env.refresh().traverse("Partly Cloudy QC").as_dir()
    records = []
    for subject in subjects:
        page = qc.traverse(subject).as_page()
        assert [type(entry) for entry in page.entries] == [
            LA.AttachmentEntry,
            LA.TextEntry,
        ]
        attachment_entry = page.entries[0]
        preview = page.entries[1].content
        downloaded = attachment_entry.content
        try:
            assert downloaded.filename == f"{subject}.json"
            downloaded.seek(0)
            records.append(json.load(downloaded))
        finally:
            downloaded.close()
        assert subject in preview

    assert [record["subject"] for record in records] == list(subjects)

    dashboard = test_env.page("Dashboards/Cohort QC")
    dashboard.entries.create_json_entry(
        {"subjects": len(records), "mean_dvars": 1.25}, filename="summary.json"
    )
    source = tmp_path / "qc-figure.svg"
    source_bytes = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
    source.write_bytes(source_bytes)
    source_attachment = LA.Attachment.from_file(source)
    try:
        dashboard.entries.create(LA.AttachmentEntry, source_attachment)
    finally:
        source_attachment.close()

    dashboard = test_env.refresh().traverse("Dashboards/Cohort QC").as_page()
    assert [type(entry) for entry in dashboard.entries] == [
        LA.AttachmentEntry,
        LA.TextEntry,
        LA.AttachmentEntry,
    ]
    summary_attachment = dashboard.entries[0].content
    try:
        assert summary_attachment.filename == "summary.json"
        assert json.load(summary_attachment) == {
            "subjects": len(subjects),
            "mean_dvars": 1.25,
        }
    finally:
        summary_attachment.close()
    assert "mean_dvars" in dashboard.entries[1].content
    figure = dashboard.entries[2].content
    try:
        assert figure.filename == source.name
        assert figure.read() == source_bytes
    finally:
        figure.close()
