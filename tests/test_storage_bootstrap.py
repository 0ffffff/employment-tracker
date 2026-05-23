from track.paths import db_path, resumes_dir, track_home
from track.storage import bootstrap_storage


def test_first_run_bootstrap_creates_directories_and_db(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    created_db = bootstrap_storage()
    assert created_db == db_path()
    assert track_home().exists()
    assert resumes_dir().exists()
    assert created_db.exists()
