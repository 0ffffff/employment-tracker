import pytest

from track.applications import add_application
from track.errors import ValidationError
from track.resumes import add_resume, set_latest_resume
from track.storage import bootstrap_storage, connection


def test_add_with_explicit_resume_creates_ghost_record(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)

    app_id = add_application("Acme SWE Intern", "base", database_path)
    with connection(database_path) as conn:
        row = conn.execute(
            "SELECT id, role_text, status FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
    assert row["id"] == app_id
    assert row["role_text"] == "Acme SWE Intern"
    assert row["status"] == "ghost"


def test_add_without_resume_ref_uses_latest(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("latest", str(resume_file), database_path)

    app_id = add_application("Globex Data Intern", None, database_path)
    assert app_id > 0


def test_add_without_latest_resume_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()

    with pytest.raises(ValidationError):
        add_application("No Resume Yet", None, database_path)


def test_add_normalizes_spacing(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)

    app_id = add_application("  Acme   SWE   Intern ", "base", database_path)
    with connection(database_path) as conn:
        row = conn.execute(
            "SELECT role_text FROM applications WHERE id = ?", (app_id,)
        ).fetchone()
    assert row["role_text"] == "Acme SWE Intern"


def test_add_without_resume_ref_uses_newly_set_latest(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("older", str(resume_file), database_path)
    add_resume("newer", str(resume_file), database_path)
    set_latest_resume("older", database_path)

    app_id = add_application("Initech Backend Intern", None, database_path)
    with connection(database_path) as conn:
        row = conn.execute(
            """
            SELECT a.id, r.nickname AS resume_nickname
            FROM applications a
            JOIN resumes r ON r.id = a.resume_id
            WHERE a.id = ?
            """,
            (app_id,),
        ).fetchone()

    assert row["id"] == app_id
    assert row["resume_nickname"] == "older"
