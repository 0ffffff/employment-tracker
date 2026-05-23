import os
import stat
import sys

import pytest

from track.applications import add_application
from track.completion_data import (
    FUZZY_COMPLETION_LIMIT,
    application_completion_candidates,
    status_completion_candidates,
)
from track.resumes import add_resume
from track.storage import bootstrap_storage, connection


def _seed_applications(monkeypatch, tmp_path, *role_texts: str):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    for text in role_texts:
        add_application(text, "base", database_path)
    return database_path


def test_application_fuzzy_partial_matches_role_text(monkeypatch, tmp_path):
    database_path = _seed_applications(
        monkeypatch,
        tmp_path,
        "Amazon SWE Intern",
        "Google STEP Intern",
    )
    out = application_completion_candidates(database_path, "Ama")
    assert "Amazon SWE Intern" in out
    assert "Google STEP Intern" not in out


def test_application_empty_db_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    with connection(database_path) as conn:
        conn.execute("DELETE FROM applications")
        conn.commit()
    assert application_completion_candidates(database_path, "x") == []


def test_application_missing_db_file_returns_empty(tmp_path):
    missing = tmp_path / "track.db"
    assert not missing.exists()
    assert application_completion_candidates(missing, "1") == []


def test_application_digit_prefix_starts_with_decimal_string(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    with connection(database_path) as conn:
        rid = int(conn.execute("SELECT id FROM resumes LIMIT 1").fetchone()["id"])
        conn.execute("DELETE FROM applications")
        for app_id, role in [(1, "Role 1"), (2, "Role 2"), (10, "Role 10"), (12, "Role 12")]:
            conn.execute(
                """
                INSERT INTO applications (id, role_text, resume_id, applied_date, status)
                VALUES (?, ?, ?, '2020-01-01', 'ghost')
                """,
                (app_id, role, rid),
            )
        conn.commit()
    out = application_completion_candidates(database_path, "1")
    assert set(out) == {"1", "10", "12"}


def test_application_leading_zero_digit_resolves_to_canonical_id(monkeypatch, tmp_path):
    database_path = _seed_applications(monkeypatch, tmp_path, "Solo Role")
    out = application_completion_candidates(database_path, "01")
    assert out == ["1"]


def test_application_whitespace_only_prefix_returns_empty(monkeypatch, tmp_path):
    database_path = _seed_applications(monkeypatch, tmp_path, "Any Role")
    assert application_completion_candidates(database_path, "") == []
    assert application_completion_candidates(database_path, "   ") == []


@pytest.mark.skipif(sys.platform == "win32", reason="chmod-based lock simulation is POSIX-specific")
def test_application_locked_db_returns_empty(monkeypatch, tmp_path):
    database_path = _seed_applications(monkeypatch, tmp_path, "Locked Co")
    mode = os.stat(database_path).st_mode
    try:
        os.chmod(database_path, 0)
        assert application_completion_candidates(database_path, "Lock") == []
    finally:
        os.chmod(database_path, stat.S_IMODE(mode))


def test_status_tokens_sorted_and_filtered():
    all_toks = status_completion_candidates("")
    assert all_toks == sorted(all_toks)
    assert "reject" in all_toks
    assert "r" in all_toks
    assert status_completion_candidates("re") == ["reject"]
    assert status_completion_candidates("R") == ["r", "reject"]


def test_fuzzy_completion_respects_limit(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    for i in range(FUZZY_COMPLETION_LIMIT + 10):
        add_application(f"Acme Corp Role {i:03d}", "base", database_path)
    out = application_completion_candidates(database_path, "Acme")
    assert len(out) == FUZZY_COMPLETION_LIMIT
