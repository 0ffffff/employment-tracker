import json

import pytest

from track.applications import add_application, list_application_rows
from track.cli import main
from track.errors import ValidationError
from track.storage import connection


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


def _seed_search_roles(database_path, seed_resume):
    seed_resume()
    add_application("Acme SWE Intern", "base", database_path)
    add_application("Google SWE Intern", "base", database_path)
    add_application("Google STEP Intern", "base", database_path)
    add_application("Alphabet (Google) PM Intern", "base", database_path)
    add_application("Meta SWE Intern", "base", database_path)


def test_list_query_ranks_fuzzy_matches(database_path, seed_resume):
    _seed_search_roles(database_path, seed_resume)
    rows = list_application_rows(database_path, role_query="google")
    roles = [row["role_text"] for row in rows]
    assert "Google SWE Intern" in roles
    assert "Google STEP Intern" in roles
    assert "Alphabet (Google) PM Intern" in roles
    assert "Acme SWE Intern" not in roles
    assert "Meta SWE Intern" not in roles
    assert roles[0] in {"Google SWE Intern", "Google STEP Intern", "Alphabet (Google) PM Intern"}


def test_list_query_is_case_insensitive(database_path, seed_resume):
    _seed_search_roles(database_path, seed_resume)
    lower = [row["role_text"] for row in list_application_rows(database_path, role_query="google")]
    upper = [row["role_text"] for row in list_application_rows(database_path, role_query="GOOGLE")]
    assert lower == upper


def test_list_query_tolerates_typos(database_path, seed_resume):
    _seed_search_roles(database_path, seed_resume)
    roles = [
        row["role_text"]
        for row in list_application_rows(database_path, role_query="gogle")
    ]
    assert "Google SWE Intern" in roles
    assert "Meta SWE Intern" not in roles


def test_list_query_does_not_treat_intel_as_intern(database_path, seed_resume):
    _seed_search_roles(database_path, seed_resume)
    add_application("Intel SWE Intern", "base", database_path)
    roles = [
        row["role_text"]
        for row in list_application_rows(database_path, role_query="intel")
    ]
    assert roles == ["Intel SWE Intern"]


def test_list_query_with_status_filter(database_path, seed_resume):
    _seed_search_roles(database_path, seed_resume)
    with connection(database_path) as conn:
        conn.execute(
            "UPDATE applications SET status = ? WHERE role_text = ?",
            ("interviewing", "Google SWE Intern"),
        )
        conn.commit()

    rows = list_application_rows(
        database_path, role_query="google", status_filter="i"
    )
    assert [row["role_text"] for row in rows] == ["Google SWE Intern"]


def test_list_query_digit_is_not_id_lookup(database_path, seed_resume):
    seed_resume()
    add_application("Acme SWE Intern", "base", database_path)
    rows = list_application_rows(database_path, role_query="1")
    assert rows == []


def test_main_list_query_empty_message(database_path, seed_resume, capsys):
    seed_resume()
    add_application("Acme SWE Intern", "base", database_path)
    assert main(["list", "zzzzunrelated"]) == 0
    assert capsys.readouterr().out.strip() == "No applications matching 'zzzzunrelated'."


def test_main_list_query_json_and_alias(database_path, seed_resume, capsys):
    _seed_search_roles(database_path, seed_resume)
    assert main(["ls", "google", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    roles = {row["role_text"] for row in payload["applications"]}
    assert "Google SWE Intern" in roles
    assert "Acme SWE Intern" not in roles
