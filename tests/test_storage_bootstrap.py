from track.paths import db_path, resumes_dir, track_home
from track.resumes import add_resume
from track.storage import bootstrap_storage, connection


def test_first_run_bootstrap_creates_directories_and_db(isolated_home):
    created_db = bootstrap_storage()
    assert created_db == db_path()
    assert track_home().exists()
    assert resumes_dir().exists()
    assert created_db.exists()


def test_bootstrap_skips_schema_when_already_initialized(database_path, resume_file):
    add_resume("base", str(resume_file), database_path)

    bootstrap_storage()

    with connection(database_path) as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM resumes").fetchone()["c"]
    assert count == 1


def test_bootstrap_recovers_from_corrupted_file(isolated_home):
    db = db_path()
    track_home().mkdir(parents=True, exist_ok=True)
    db.write_text("NOT A DATABASE", encoding="utf-8")

    bootstrap_storage()

    # A fresh, valid SQLite database should be created at the original path.
    assert db.exists()
    assert db.read_bytes()[:16] == b"SQLite format 3\x00"

    # The corrupted file should be preserved under a backup name.
    backups = list(track_home().glob("track.db.corrupt*"))
    assert backups, "expected a backup of the corrupted database file"
    assert backups[0].read_text(encoding="utf-8") == "NOT A DATABASE"
