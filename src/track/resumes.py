"""Resume registration (copy into managed storage) and listing."""

import shutil
import sqlite3
import tempfile
from pathlib import Path

from track.errors import NotFoundError, ValidationError
from track.paths import resumes_dir
from track.storage import connection


def _latest_resume_id(conn) -> int | None:
    row = conn.execute("SELECT id FROM resumes WHERE is_latest = 1 LIMIT 1").fetchone()
    return int(row["id"]) if row else None


def add_resume(nickname: str, source_path: str, database_path: Path) -> int:
    source = Path(source_path).expanduser()
    if not source.exists() or not source.is_file():
        raise NotFoundError(
            f"Resume file '{source_path}' was not found. Provide a readable local file."
        )
    if not nickname.strip():
        raise ValidationError("Resume nickname cannot be empty.")

    extension = source.suffix
    resumes_directory = resumes_dir()
    with tempfile.NamedTemporaryFile(
        dir=resumes_directory, prefix="tmp-", suffix=extension, delete=False
    ) as tmp_file:
        temp_path = Path(tmp_file.name)
    shutil.copy2(source, temp_path)

    previous_latest: int | None = None
    try:
        with connection(database_path) as conn:
            previous_latest = _latest_resume_id(conn)
            conn.execute("UPDATE resumes SET is_latest = 0 WHERE is_latest = 1")
            cursor = conn.execute(
                """
                INSERT INTO resumes (nickname, managed_path, is_latest)
                VALUES (?, ?, 1)
                """,
                (nickname.strip(), str(temp_path)),
            )
            resume_id = int(cursor.lastrowid)
            conn.commit()
    except sqlite3.IntegrityError as exc:
        temp_path.unlink(missing_ok=True)
        raise ValidationError(
            f"Resume nickname '{nickname.strip()}' already exists. Choose a distinct nickname."
        ) from exc
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    final_path = resumes_directory / f"{resume_id}{extension}"
    try:
        temp_path.replace(final_path)
        with connection(database_path) as conn:
            conn.execute(
                "UPDATE resumes SET managed_path = ? WHERE id = ?",
                (str(final_path), resume_id),
            )
            conn.commit()
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        with connection(database_path) as conn:
            conn.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
            if previous_latest is not None:
                conn.execute(
                    "UPDATE resumes SET is_latest = 1 WHERE id = ?", (previous_latest,)
                )
            conn.commit()
        raise ValidationError(f"Failed to finalize managed resume copy: {exc}") from exc

    return resume_id


def list_resume_rows(database_path: Path) -> list[dict]:
    with connection(database_path) as conn:
        rows = conn.execute(
            """
            SELECT id, nickname, managed_path, is_latest, created_at
            FROM resumes
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()

    return [
        {
            "id": int(row["id"]),
            "nickname": row["nickname"],
            "managed_path": row["managed_path"],
            "is_latest": bool(row["is_latest"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
