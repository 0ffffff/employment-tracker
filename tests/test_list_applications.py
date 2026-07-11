import json

import pytest

from track.applications import list_application_rows
from track.cli import main
from track.errors import ValidationError


def test_list_orders_by_applied_date_then_id_desc(seeded_filtered_applications):
    database_path, earlier, later = seeded_filtered_applications
    rows = list_application_rows(database_path)
    assert [row["role_text"] for row in rows] == ["Newer Role", "Older Role"]
    assert rows[0]["applied_date"] == later
    assert rows[1]["applied_date"] == earlier


def test_list_filters_by_status(seeded_filtered_applications):
    database_path, *_ = seeded_filtered_applications
    rows = list_application_rows(database_path, status_filter="g")
    assert len(rows) == 1
    assert rows[0]["role_text"] == "Older Role"


def test_list_filters_applied_date_range(seeded_filtered_applications):
    database_path, earlier, later = seeded_filtered_applications
    rows = list_application_rows(database_path, applied_from=earlier, applied_to=later)
    assert {row["role_text"] for row in rows} == {"Older Role", "Newer Role"}


def test_list_invalid_status_raises(seeded_filtered_applications):
    database_path, *_ = seeded_filtered_applications
    with pytest.raises(ValidationError):
        list_application_rows(database_path, status_filter="not-a-status")


def test_main_list_json_output(seeded_filtered_applications, capsys):
    seeded_filtered_applications
    assert main(["list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["format_version"] == 1
    assert len(payload["applications"]) == 2
    keys = set(payload["applications"][0].keys())
    assert keys == {"id", "role_text", "status", "applied_date", "resume_nickname"}


def test_main_list_human_truncates_with_total(seed_role_apps, capsys):
    seed_role_apps(8)
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 7  # header + 5 rows + ellipsis line
    assert "... 8 applications total" in out
    assert "Role 7" in out
    assert "Role 3" in out
    assert "Role 2" not in out
    assert "Role 0" not in out


def test_main_list_all_shows_every_row(seed_role_apps, capsys):
    seed_role_apps(8)
    assert main(["list", "--all"]) == 0
    out = capsys.readouterr().out
    assert "... 8 applications total" not in out
    assert "Role 0" in out
    assert "Role 7" in out
