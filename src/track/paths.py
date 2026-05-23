from pathlib import Path


def track_home() -> Path:
    return Path.home() / ".track"


def resumes_dir() -> Path:
    return track_home() / "resumes"


def db_path() -> Path:
    return track_home() / "track.db"


def ensure_track_dirs() -> None:
    track_home().mkdir(parents=True, exist_ok=True)
    resumes_dir().mkdir(parents=True, exist_ok=True)
