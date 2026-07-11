"""Application CRUD, status normalization, list filters, and fuzzy identifier resolution."""

from datetime import date
from pathlib import Path

from track.confirm import choose_candidate, confirm_status_change
from track.errors import NonInteractiveError, NotFoundError, ValidationError
from track.fuzzy import FUZZY_MATCH_THRESHOLD, candidate_matches
from track.storage import connection

_CANONICAL_STATUSES = ("reject", "interviewing", "offer", "accepted", "ghost")
_STATUS_SHORT = ("r", "i", "o", "a", "g")
STATUS_ALIASES = {s: s for s in _CANONICAL_STATUSES} | dict(
    zip(_STATUS_SHORT, _CANONICAL_STATUSES, strict=True)
)


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
        return int(cursor.lastrowid or 0)


def _parse_applied_date(label: str, raw: str) -> str:
    try:
        return date.fromisoformat(raw.strip()).isoformat()
    except ValueError as exc:
        raise ValidationError(
            f"{label} must be a valid date in YYYY-MM-DD format."
        ) from exc


def list_application_rows(
    database_path: Path,
    *,
    status_filter: str | None = None,
    applied_from: str | None = None,
    applied_to: str | None = None,
) -> list[dict]:
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
    params: list[str] = []
    if status_filter is not None:
        query += " AND a.status = ?"
        params.append(normalize_status(status_filter))
    if applied_from is not None:
        query += " AND a.applied_date >= ?"
        params.append(_parse_applied_date("--applied-from", applied_from))
    if applied_to is not None:
        query += " AND a.applied_date <= ?"
        params.append(_parse_applied_date("--applied-to", applied_to))
    query += " ORDER BY a.applied_date DESC, a.id DESC"

    with connection(database_path) as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "id": int(row["id"]),
            "role_text": row["role_text"],
            "status": row["status"],
            "applied_date": row["applied_date"],
            "resume_nickname": row["resume_nickname"],
        }
        for row in rows
    ]


def normalize_status(status: str) -> str:
    canonical = STATUS_ALIASES.get(status.lower().strip())
    if not canonical:
        raise ValidationError(
            f"Unknown status '{status}'. "
            "Use one of: reject|r, interviewing|i, offer|o, accepted|a, ghost|g."
        )
    return canonical


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _application_role_candidates(conn) -> list[dict[str, int | str]]:
    rows = conn.execute("SELECT id, role_text FROM applications").fetchall()
    return [{"id": int(row["id"]), "role_text": row["role_text"]} for row in rows]


def _prefix_application_role_candidates(conn, query: str) -> list[dict[str, int | str]]:
    escaped = _escape_like(query.strip())
    rows = conn.execute(
        """
        SELECT id, role_text FROM applications
        WHERE role_text LIKE ? ESCAPE '\\' COLLATE NOCASE
        """,
        (f"{escaped}%",),
    ).fetchall()
    return [{"id": int(row["id"]), "role_text": row["role_text"]} for row in rows]


def _fuzzy_application_matches(conn, query: str, threshold: int) -> list[dict[str, int | str | float]]:
    prefix_candidates = _prefix_application_role_candidates(conn, query)
    matches = candidate_matches(query, prefix_candidates, threshold=threshold)
    if matches:
        return matches
    return candidate_matches(
        query, _application_role_candidates(conn), threshold=threshold
    )


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

    matches = _fuzzy_application_matches(conn, stripped, FUZZY_MATCH_THRESHOLD)
    if not matches:
        raise NotFoundError(
            f"No application matched '{identifier}' with a score of at least "
            f"{FUZZY_MATCH_THRESHOLD}."
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
        if not force and not is_tty:
            raise NonInteractiveError(
                "Confirmation required for updates in non-interactive mode. Use -f."
            )
        if not force:
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
