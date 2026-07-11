from pathlib import Path

import pytest

from track.errors import NotFoundError, ValidationError
from track.paths import resumes_dir
from track.resumes import add_resume, set_latest_resume
from track.storage import connection


def test_add_resume_persists_record_and_updates_latest(database_path, resume_file):
    first_id = add_resume("base", str(resume_file), database_path)
    second_id = add_resume("tailored", str(resume_file), database_path)

    with connection(database_path) as conn:
        latest = conn.execute(
            "SELECT id, nickname, managed_path FROM resumes WHERE is_latest = 1"
        ).fetchone()
    assert latest["id"] == second_id
    assert latest["nickname"] == "tailored"
    assert Path(latest["managed_path"]).exists()
    assert Path(latest["managed_path"]).parent == resumes_dir()
    assert first_id != second_id


def test_duplicate_resume_nickname_fails(database_path, resume_file):
    add_resume("base", str(resume_file), database_path)

    with pytest.raises(ValidationError):
        add_resume("base", str(resume_file), database_path)


def test_missing_resume_file_fails_without_db_side_effects(database_path, isolated_home):
    with pytest.raises(NotFoundError):
        add_resume("missing", str(isolated_home / "does-not-exist.pdf"), database_path)

    with connection(database_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM resumes").fetchone()["c"]
    assert count == 0


def test_set_latest_resume_switches_latest(database_path, resume_file):
    first_id = add_resume("first", str(resume_file), database_path)
    second_id = add_resume("second", str(resume_file), database_path)

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


def test_set_latest_resume_allows_idempotent_repeat(database_path, resume_file):
    latest_id = add_resume("base", str(resume_file), database_path)

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


def test_set_latest_resume_missing_name_fails_without_mutation(database_path, resume_file):
    add_resume("base", str(resume_file), database_path)

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
