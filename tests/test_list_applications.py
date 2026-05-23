import json
from datetime import date, timedelta

import pytest

from track.applications import add_application, list_application_rows
from track.cli import main
from track.errors import ValidationError
from track.resumes import add_resume
from track.storage import bootstrap_storage, connection


def _seed_applications(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    add_resume("alt", str(resume_file), database_path)

    today = date.today()
    earlier = (today - timedelta(days=5)).isoformat()
    later = (today - timedelta(days=1)).isoformat()

    add_application("Older Role", "base", database_path)
    add_application("Newer Role", "alt", database_path)

    with connection(database_path) as conn:
        conn.execute(
            "UPDATE applications SET applied_date = ?, status = ? WHERE role_text = ?",
            (earlier, "ghost", "Older Role"),
        )
        conn.execute(
            "UPDATE applications SET applied_date = ?, status = ? WHERE role_text = ?",
            (later, "interviewing", "Newer Role"),
        )
        conn.commit()

    return database_path, earlier, later


def test_list_orders_by_applied_date_then_id_desc(monkeypatch, tmp_path):
    database_path, earlier, later = _seed_applications(monkeypatch, tmp_path)
    rows = list_application_rows(database_path)
    assert [row["role_text"] for row in rows] == ["Newer Role", "Older Role"]
    assert rows[0]["applied_date"] == later
    assert rows[1]["applied_date"] == earlier


def test_list_filters_by_status(monkeypatch, tmp_path):
    database_path, *_ = _seed_applications(monkeypatch, tmp_path)
    rows = list_application_rows(database_path, status_filter="g")
    assert len(rows) == 1
    assert rows[0]["role_text"] == "Older Role"


def test_list_filters_applied_date_range(monkeypatch, tmp_path):
    database_path, earlier, later = _seed_applications(monkeypatch, tmp_path)
    rows = list_application_rows(database_path, applied_from=earlier, applied_to=later)
    assert {row["role_text"] for row in rows} == {"Older Role", "Newer Role"}


def test_list_invalid_status_raises(monkeypatch, tmp_path):
    database_path, *_ = _seed_applications(monkeypatch, tmp_path)
    with pytest.raises(ValidationError):
        list_application_rows(database_path, status_filter="not-a-status")


def test_main_list_json_output(monkeypatch, tmp_path, capsys):
    database_path, *_ = _seed_applications(monkeypatch, tmp_path)
    assert main(["list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["format_version"] == 1
    assert len(payload["applications"]) == 2
    keys = set(payload["applications"][0].keys())
    assert keys == {"id", "role_text", "status", "applied_date", "resume_nickname"}


def _seed_many_applications(monkeypatch, tmp_path, count: int):
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    for index in range(count):
        add_application(f"Role {index}", "base", database_path)
    return database_path


def test_main_list_human_truncates_with_total(monkeypatch, tmp_path, capsys):
    _seed_many_applications(monkeypatch, tmp_path, count=8)
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 7  # header + 5 rows + ellipsis line
    assert "... 8 applications total" in out
    assert "Role 7" in out
    assert "Role 3" in out
    assert "Role 2" not in out
    assert "Role 0" not in out


def test_main_list_all_shows_every_row(monkeypatch, tmp_path, capsys):
    _seed_many_applications(monkeypatch, tmp_path, count=8)
    assert main(["list", "--all"]) == 0
    out = capsys.readouterr().out
    assert "... 8 applications total" not in out
    assert "Role 0" in out
    assert "Role 7" in out
