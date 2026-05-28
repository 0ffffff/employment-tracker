from pathlib import Path

import pytest

from track.errors import NotFoundError, ValidationError
from track.paths import resumes_dir
from track.resumes import add_resume, set_latest_resume
from track.storage import bootstrap_storage, connection


def _write_resume(path: Path, text: str = "resume") -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_add_resume_persists_record_and_updates_latest(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    source = _write_resume(tmp_path / "resume.pdf")

    first_id = add_resume("base", str(source), database_path)
    second_id = add_resume("tailored", str(source), database_path)

    with connection(database_path) as conn:
        latest = conn.execute(
            "SELECT id, nickname, managed_path FROM resumes WHERE is_latest = 1"
        ).fetchone()
    assert latest["id"] == second_id
    assert latest["nickname"] == "tailored"
    assert Path(latest["managed_path"]).exists()
    assert Path(latest["managed_path"]).parent == resumes_dir()
    assert first_id != second_id


def test_duplicate_resume_nickname_fails(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    source = _write_resume(tmp_path / "resume.pdf")
    add_resume("base", str(source), database_path)

    with pytest.raises(ValidationError):
        add_resume("base", str(source), database_path)


def test_missing_resume_file_fails_without_db_side_effects(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()

    with pytest.raises(NotFoundError):
        add_resume("missing", str(tmp_path / "does-not-exist.pdf"), database_path)

    with connection(database_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM resumes").fetchone()["c"]
    assert count == 0


def test_set_latest_resume_switches_latest(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    source = _write_resume(tmp_path / "resume.pdf")
    first_id = add_resume("first", str(source), database_path)
    second_id = add_resume("second", str(source), database_path)

    latest_id = set_latest_resume("first", database_path)

    assert latest_id == first_id
    with connection(database_path) as conn:
        latest = conn.execute(
            "SELECT id, nickname FROM resumes WHERE is_latest = 1"
        ).fetchone()
        latest_count = conn.execute(
            "SELECT COUNT(*) AS c FROM resumes WHERE is_latest = 1"
        ).fetchone()["c"]
    assert latest["id"] == first_id
    assert latest["nickname"] == "first"
    assert second_id != first_id
    assert latest_count == 1


def test_set_latest_resume_allows_idempotent_repeat(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    source = _write_resume(tmp_path / "resume.pdf")
    latest_id = add_resume("base", str(source), database_path)

    returned_id = set_latest_resume("base", database_path)

    assert returned_id == latest_id
    with connection(database_path) as conn:
        latest_count = conn.execute(
            "SELECT COUNT(*) AS c FROM resumes WHERE is_latest = 1"
        ).fetchone()["c"]
        latest = conn.execute(
            "SELECT id FROM resumes WHERE is_latest = 1 LIMIT 1"
        ).fetchone()
    assert latest_count == 1
    assert latest["id"] == latest_id


def test_set_latest_resume_missing_name_fails_without_mutation(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    source = _write_resume(tmp_path / "resume.pdf")
    add_resume("base", str(source), database_path)

    with pytest.raises(NotFoundError):
        set_latest_resume("missing", database_path)

    with connection(database_path) as conn:
        latest = conn.execute(
            "SELECT nickname FROM resumes WHERE is_latest = 1 LIMIT 1"
        ).fetchone()
        latest_count = conn.execute(
            "SELECT COUNT(*) AS c FROM resumes WHERE is_latest = 1"
        ).fetchone()["c"]
    assert latest["nickname"] == "base"
    assert latest_count == 1
