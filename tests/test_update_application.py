import pytest

from track.applications import add_application, update_application_status
from track.errors import NonInteractiveError, NotFoundError
from track.fuzzy import FUZZY_MATCH_THRESHOLD
from track.storage import connection


def test_update_by_numeric_id_with_full_status(seeded_application):
    database_path, app_id = seeded_application

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


def test_non_tty_update_requires_force(seeded_application):
    database_path, app_id = seeded_application

    with pytest.raises(NonInteractiveError):
        update_application_status(
            identifier=str(app_id),
            raw_status="i",
            database_path=database_path,
            force=False,
            is_tty=False,
        )


def test_non_tty_with_force_succeeds(seeded_application):
    database_path, app_id = seeded_application

    updated_id, status = update_application_status(
        identifier=str(app_id),
        raw_status="a",
        database_path=database_path,
        force=True,
        is_tty=False,
    )
    assert updated_id == app_id
    assert status == "accepted"


def test_update_by_fuzzy_role_text(seeded_application):
    database_path, app_id = seeded_application

    updated_id, status = update_application_status(
        identifier="Acme SWE",
        raw_status="i",
        database_path=database_path,
        force=True,
        is_tty=False,
    )
    assert updated_id == app_id
    assert status == "interviewing"


def test_exact_role_text_skips_fuzzy_disambiguation(database_path, seed_resume):
    seed_resume()
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


def test_fuzzy_match_falls_back_when_query_is_not_a_prefix(seeded_application):
    database_path, _app_id = seeded_application
    add_application("Alpha Beta Gamma Role", "base", database_path)

    updated_id, status = update_application_status(
        identifier="Beta Gamma",
        raw_status="i",
        database_path=database_path,
        force=True,
        is_tty=False,
    )
    assert status == "interviewing"
    with connection(database_path) as conn:
        row = conn.execute(
            "SELECT id, status FROM applications WHERE role_text = ?",
            ("Alpha Beta Gamma Role",),
        ).fetchone()
    assert row["id"] == updated_id
    assert row["status"] == "interviewing"


def test_fuzzy_no_match_raises_not_found(seeded_application):
    database_path, _app_id = seeded_application

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
