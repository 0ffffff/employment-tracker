from pathlib import Path

import click
import pytest
from click.shell_completion import BashComplete

from track.applications import add_application
from track.cli import (
    cli,
    complete_application_identifier,
    complete_status_token,
    main,
)
from track.resumes import add_resume
from track.storage import bootstrap_storage


def _completion_values(items: list[click.shell_completion.CompletionItem]) -> list[str]:
    return [item.value for item in items]


def _seed_applications(tmp_path: Path) -> None:
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    add_application("Amazon SWE Intern", "base", database_path)


def test_complete_application_identifier_fuzzy(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _seed_applications(tmp_path)

    values = _completion_values(complete_application_identifier(None, None, "Ama"))

    assert "Amazon SWE Intern" in values


def test_complete_application_identifier_two_acme_matches(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    database_path = bootstrap_storage()
    resume_file = tmp_path / "resume.pdf"
    resume_file.write_text("resume", encoding="utf-8")
    add_resume("base", str(resume_file), database_path)
    add_application("Acme SWE Intern", "base", database_path)
    add_application("Acme Data Intern", "base", database_path)

    values = _completion_values(complete_application_identifier(None, None, "Acme"))

    assert "Acme SWE Intern" in values
    assert "Acme Data Intern" in values


def test_complete_application_identifier_digit_prefix(
    monkeypatch, tmp_path: Path,
) -> None:
    from track.storage import connection

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

    values = _completion_values(complete_application_identifier(None, None, "1"))

    assert set(values) == {"1", "10", "12"}


def test_complete_application_identifier_empty_prefix_returns_empty(
    monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _seed_applications(tmp_path)

    assert complete_application_identifier(None, None, "") == []
    assert complete_application_identifier(None, None, "   ") == []


def test_complete_application_identifier_missing_db_returns_empty(
    monkeypatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    assert complete_application_identifier(None, None, "Ama") == []


def test_complete_status_token_interviewing_prefix() -> None:
    values = _completion_values(complete_status_token(None, None, "i"))

    assert "interviewing" in values


def test_bash_complete_update_identifier_fuzzy(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _seed_applications(tmp_path)

    monkeypatch.setenv("COMP_WORDS", "track update Ama")
    monkeypatch.setenv("COMP_CWORD", "2")

    comp = BashComplete(cli, {}, "track", "_TRACK_COMPLETE")
    args, incomplete = comp.get_completion_args()
    assert args == ["update"]
    assert incomplete == "Ama"

    values = _completion_values(comp.get_completions(args, incomplete))
    assert "Amazon SWE Intern" in values


def test_bash_complete_update_status_prefix(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    _seed_applications(tmp_path)

    monkeypatch.setenv("COMP_WORDS", "track update 1 i")
    monkeypatch.setenv("COMP_CWORD", "3")

    comp = BashComplete(cli, {}, "track", "_TRACK_COMPLETE")
    args, incomplete = comp.get_completion_args()
    assert args == ["update", "1"]
    assert incomplete == "i"

    values = _completion_values(comp.get_completions(args, incomplete))
    assert "interviewing" in values


def test_main_list_json_without_completion_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    bootstrap_storage()

    assert main(["list", "--json"]) == 0


def test_zsh_completion_source_registers_track_and_suppresses_empty() -> None:
    from click.shell_completion import get_completion_class

    from track import shell_completion  # noqa: F401

    zsh_cls = get_completion_class("zsh")
    assert zsh_cls is shell_completion.TrackZshComplete
    source = zsh_cls(cli, {}, "track", "_TRACK_COMPLETE").source()
    assert "compdef" in source and "track" in source
    assert "_message ''" in source


def test_bash_completion_source_quotes_plain_values() -> None:
    from click.shell_completion import get_completion_class

    from track import shell_completion  # noqa: F401

    bash_cls = get_completion_class("bash")
    assert bash_cls is shell_completion.TrackBashComplete
    source = bash_cls(cli, {}, "track", "_TRACK_COMPLETE").source()
    assert 'COMPREPLY+=("$value")' in source
    assert "compopt +o default" in source
