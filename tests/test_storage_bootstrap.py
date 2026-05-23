from track.paths import db_path, resumes_dir, track_home
from track.storage import bootstrap_storage


def test_first_run_bootstrap_creates_directories_and_db(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    created_db = bootstrap_storage()
    assert created_db == db_path()
    assert track_home().exists()
    assert resumes_dir().exists()
    assert created_db.exists()


def test_bootstrap_recovers_from_corrupted_file(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    db = db_path()
    track_home().mkdir(parents=True, exist_ok=True)
    db.write_text("NOT A DATABASE", encoding="utf-8")

    bootstrap_storage()

    assert db.exists()
    assert db.read_bytes()[:16] == b"SQLite format 3\x00"
