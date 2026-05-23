"""Default on-disk locations under ~/.track/."""

from pathlib import Path


def track_home() -> Path:
    return Path.home() / ".track"


def resumes_dir() -> Path:
    return track_home() / "resumes"


def db_path() -> Path:
    return track_home() / "track.db"


def ensure_track_dirs() -> None:
    home = track_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "resumes").mkdir(parents=True, exist_ok=True)
