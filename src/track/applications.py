from datetime import date
from pathlib import Path
from typing import Any

from track.confirm import choose_candidate, confirm_status_change
from track.errors import NonInteractiveError, NotFoundError, ValidationError
from track.fuzzy import candidate_matches
from track.storage import connection

STATUS_ALIASES = {
    "reject": "reject",
    "r": "reject",
    "interviewing": "interviewing",
    "i": "interviewing",
    "offer": "offer",
    "o": "offer",
    "accepted": "accepted",
    "a": "accepted",
    "ghost": "ghost",
    "g": "ghost",
}


def normalize_role_text(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        raise ValidationError("Company and position text cannot be empty.")
    return normalized


def _resume_for_add(conn, resume_ref: str | None) -> int:
    if resume_ref:
        row = conn.execute(
            "SELECT id FROM resumes WHERE nickname = ? LIMIT 1", (resume_ref,)
        ).fetchone()
        if not row:
            raise NotFoundError(f"Resume reference '{resume_ref}' was not found.")
        return int(row["id"])

    latest = conn.execute(
        "SELECT id FROM resumes WHERE is_latest = 1 LIMIT 1"
    ).fetchone()
    if not latest:
        raise ValidationError(
            "No latest resume found. Run `track add-resume <nickname> <path>` first "
            "or pass -r <resume_ref>."
        )
    return int(latest["id"])


def add_application(role_text: str, resume_ref: str | None, database_path: Path) -> int:
    normalized_role = normalize_role_text(role_text)
    with connection(database_path) as conn:
        resume_id = _resume_for_add(conn, resume_ref)
        cursor = conn.execute(
            """
            INSERT INTO applications (role_text, resume_id, applied_date, status)
            VALUES (?, ?, ?, ?)
            """,
            (normalized_role, resume_id, date.today().isoformat(), "ghost"),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _parse_applied_date(label: str, raw: str) -> str:
    try:
        return date.fromisoformat(raw.strip()).isoformat()
    except ValueError as exc:
        raise ValidationError(f"{label} must be a valid date in YYYY-MM-DD format.") from exc


def list_application_rows(
    database_path: Path,
    *,
    status_filter: str | None = None,
    applied_from: str | None = None,
    applied_to: str | None = None,
) -> list[dict[str, Any]]:
    status_value: str | None = None
    if status_filter is not None:
        status_value = normalize_status(status_filter)

    lower_bound: str | None = None
    upper_bound: str | None = None
    if applied_from is not None:
        lower_bound = _parse_applied_date("--applied-from", applied_from)
    if applied_to is not None:
        upper_bound = _parse_applied_date("--applied-to", applied_to)

    query = """
        SELECT
            a.id,
            a.role_text,
            a.status,
            a.applied_date,
            r.nickname AS resume_nickname
        FROM applications a
        JOIN resumes r ON r.id = a.resume_id
        WHERE 1 = 1
    """
    params: list[str | int] = []
    if status_value is not None:
        query += " AND a.status = ?"
        params.append(status_value)
    if lower_bound is not None:
        query += " AND a.applied_date >= ?"
        params.append(lower_bound)
    if upper_bound is not None:
        query += " AND a.applied_date <= ?"
        params.append(upper_bound)

    query += " ORDER BY a.applied_date DESC, a.id DESC"

    with connection(database_path) as conn:
        rows = conn.execute(query, params).fetchall()

    applications: list[dict[str, Any]] = []
    for row in rows:
        applications.append(
            {
                "id": int(row["id"]),
                "role_text": row["role_text"],
                "status": row["status"],
                "applied_date": row["applied_date"],
                "resume_nickname": row["resume_nickname"],
            }
        )
    return applications


def normalize_status(status: str) -> str:
    canonical = STATUS_ALIASES.get(status.lower().strip())
    if not canonical:
        valid = ", ".join(["reject|r", "interviewing|i", "offer|o", "accepted|a", "ghost|g"])
        raise ValidationError(f"Unknown status '{status}'. Use one of: {valid}.")
    return canonical


def _get_application_by_id(conn, application_id: int):
    row = conn.execute(
        "SELECT id, role_text, status FROM applications WHERE id = ? LIMIT 1",
        (application_id,),
    ).fetchone()
    if not row:
        raise NotFoundError(f"Application ID {application_id} was not found.")
    return row


def _resolve_application_id(
    conn,
    identifier: str,
    is_tty: bool,
    input_fn=input,
    output_fn=print,
) -> int:
    stripped = identifier.strip()
    if stripped.isdigit():
        application_id = int(stripped)
        _get_application_by_id(conn, application_id)
        return application_id

    rows = conn.execute("SELECT id, role_text FROM applications").fetchall()
    candidates = [{"id": int(row["id"]), "role_text": row["role_text"]} for row in rows]
    matches = candidate_matches(stripped, candidates, threshold=85)
    if not matches:
        raise NotFoundError(
            f"No application matched '{identifier}' with a score of at least 85."
        )
    if len(matches) == 1:
        return int(matches[0]["id"])
    if not is_tty:
        raise NonInteractiveError(
            "Multiple applications matched and disambiguation requires a TTY. "
            "Use an ID or run interactively."
        )
    return choose_candidate(matches, input_fn=input_fn, output_fn=output_fn)


def update_application_status(
    identifier: str,
    raw_status: str,
    database_path: Path,
    force: bool = False,
    is_tty: bool = True,
    input_fn=input,
    output_fn=print,
) -> tuple[int, str]:
    new_status = normalize_status(raw_status)
    with connection(database_path) as conn:
        application_id = _resolve_application_id(
            conn, identifier, is_tty, input_fn=input_fn, output_fn=output_fn
        )
        current = _get_application_by_id(conn, application_id)
        if not force:
            if not is_tty:
                raise NonInteractiveError(
                    "Confirmation required for updates in non-interactive mode. Use -f."
                )
            confirm_status_change(
                application_id=application_id,
                role_text=current["role_text"],
                old_status=current["status"],
                new_status=new_status,
                input_fn=input_fn,
                output_fn=output_fn,
            )

        conn.execute(
            "UPDATE applications SET status = ? WHERE id = ?",
            (new_status, application_id),
        )
        conn.commit()
    return application_id, new_status
