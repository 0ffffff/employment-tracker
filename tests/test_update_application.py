import pytest

from track.applications import add_application, update_application_status
from track.fuzzy import FUZZY_MATCH_THRESHOLD
from track.errors import NonInteractiveError, NotFoundError
from track.resumes import add_resume
from track.storage import bootstrap_storage, connection


def _seed(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    app_id = add_application("Acme SWE Intern", "base", database_path)
    return database_path, app_id


def test_update_by_numeric_id_with_full_status(monkeypatch, tmp_path):
    database_path, app_id = _seed(monkeypatch, tmp_path)

    updated_id, status = update_application_status(
        identifier=str(app_id),
        raw_status="interviewing",
        database_path=database_path,
        force=True,
        is_tty=False,
    )

    assert updated_id == app_id
    assert status == "interviewing"
    with connection(database_path) as conn:
        row = conn.execute(
            "SELECT status FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
    assert row["status"] == "interviewing"


def test_non_tty_update_requires_force(monkeypatch, tmp_path):
    database_path, app_id = _seed(monkeypatch, tmp_path)

    with pytest.raises(NonInteractiveError):
        update_application_status(
            identifier=str(app_id),
            raw_status="i",
            database_path=database_path,
            force=False,
            is_tty=False,
        )


def test_non_tty_with_force_succeeds(monkeypatch, tmp_path):
    database_path, app_id = _seed(monkeypatch, tmp_path)

    updated_id, status = update_application_status(
        identifier=str(app_id),
        raw_status="a",
        database_path=database_path,
        force=True,
        is_tty=False,
    )
    assert updated_id == app_id
    assert status == "accepted"


def test_update_by_fuzzy_role_text(monkeypatch, tmp_path):
    database_path, app_id = _seed(monkeypatch, tmp_path)

    updated_id, status = update_application_status(
        identifier="Acme SWE",
        raw_status="i",
        database_path=database_path,
        force=True,
        is_tty=False,
    )
    assert updated_id == app_id
    assert status == "interviewing"


def test_exact_role_text_skips_fuzzy_disambiguation(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    add_application("hello 1", "base", database_path)
    add_application("hello 2", "base", database_path)
    hello3_id = add_application("hello 3", "base", database_path)

    updated_id, status = update_application_status(
        identifier="hello 3",
        raw_status="g",
        database_path=database_path,
        force=True,
        is_tty=True,
    )
    assert updated_id == hello3_id
    assert status == "ghost"


def test_fuzzy_no_match_raises_not_found(monkeypatch, tmp_path):
    database_path, _app_id = _seed(monkeypatch, tmp_path)

    with pytest.raises(
        NotFoundError, match=f"score of at least {FUZZY_MATCH_THRESHOLD}"
    ):
        update_application_status(
            identifier="Totally Unrelated Corp",
            raw_status="i",
            database_path=database_path,
            force=True,
            is_tty=False,
        )
