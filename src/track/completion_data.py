"""Read-only SQLite helpers for shell tab completion (no bootstrap, no writes)."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from track.applications import STATUS_ALIASES
from track.fuzzy import candidate_matches

FUZZY_COMPLETION_LIMIT = 50
_SQL_PREFILTER_LIMIT = 200


def _escape_like_prefix(prefix: str) -> str:
    return (
        prefix.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _connect_readonly(database_path: Path) -> sqlite3.Connection | None:
    if not database_path.is_file():
        return None
    try:
        uri = database_path.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=0.1)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous = OFF;")
        try:
            conn.execute("PRAGMA journal_mode = WAL;")
        except sqlite3.Error:
            # Read-only URI cannot switch journal mode; existing WAL DB still reads fine.
            pass
        return conn
    except sqlite3.Error as exc:
        if os.environ.get("TRACK_DEBUG_COMPLETION"):
            print(f"track completion: open DB read-only failed: {exc}", file=sys.stderr)
        return None


def _close_quietly(conn: sqlite3.Connection | None) -> None:
    if conn is None:
        return
    try:
        conn.close()
    except sqlite3.Error:
        pass


def _prefix_application_rows(conn: sqlite3.Connection, prefix: str) -> list[sqlite3.Row]:
    pattern = _escape_like_prefix(prefix) + "%"
    return conn.execute(
        """
        SELECT id, role_text FROM applications
        WHERE role_text LIKE ? ESCAPE '\\' COLLATE NOCASE
        LIMIT ?
        """,
        (pattern, _SQL_PREFILTER_LIMIT),
    ).fetchall()


def application_completion_candidates(database_path: Path, prefix: str) -> list[str]:
    stripped = prefix.strip()
    if not stripped:
        return []

    conn = _connect_readonly(database_path)
    if conn is None:
        return []

    try:
        if stripped.isdigit():
            rows = conn.execute("SELECT id, role_text FROM applications").fetchall()
            return _digit_application_id_strings(rows, stripped)

        rows = _prefix_application_rows(conn, stripped)
        if not rows:
            return []

        candidates = [{"id": int(r["id"]), "role_text": r["role_text"]} for r in rows]
        matches = candidate_matches(stripped, candidates, threshold=85)
        matches.sort(key=lambda m: (-float(m["score"]), -int(m["id"])))
        matches = matches[:FUZZY_COMPLETION_LIMIT]
        return [str(m["role_text"]) for m in matches]
    except sqlite3.Error as exc:
        if os.environ.get("TRACK_DEBUG_COMPLETION"):
            print(f"track completion: applications query failed: {exc}", file=sys.stderr)
        return []
    finally:
        _close_quietly(conn)


def _digit_application_id_strings(rows: list[sqlite3.Row], stripped: str) -> list[str]:
    ids = [int(r["id"]) for r in rows]
    present = set(ids)
    out: set[str] = set()
    resolved = int(stripped)
    if resolved in present:
        out.add(str(resolved))
    for i in ids:
        if str(i).startswith(stripped):
            out.add(str(i))
    return sorted(out, key=int)


def status_completion_candidates(prefix: str) -> list[str]:
    keys = sorted(STATUS_ALIASES.keys())
    p = prefix.lower().strip()
    if not p:
        return list(keys)
    return [k for k in keys if k.startswith(p)]
