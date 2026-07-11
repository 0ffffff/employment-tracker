"""SQLite connection lifecycle and first-run schema bootstrap."""

import sqlite3
from pathlib import Path

from track.paths import db_path, ensure_track_dirs


def connection(database_path: Path | None = None) -> sqlite3.Connection:
    path = database_path or db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.commit()


def _schema_initialized(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'applications' LIMIT 1"
    ).fetchone()
    return row is not None


def bootstrap_storage(database_path: Path | None = None) -> Path:
    ensure_track_dirs()
    path = database_path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with connection(path) as conn:
            if not _schema_initialized(conn):
                init_db(conn)
    except sqlite3.DatabaseError as exc:
        if "file is not a database" not in str(exc):
            raise
        # Preserve the corrupted database file for potential manual recovery.
        backup = path.with_suffix(path.suffix + ".corrupt")
        counter = 1
        while backup.exists():
            backup = path.with_suffix(path.suffix + f".corrupt.{counter}")
            counter += 1
        if path.exists():
            path.replace(backup)
        with connection(path) as conn:
            init_db(conn)
    return path
