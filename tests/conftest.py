import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from track.applications import add_application
from track.resumes import add_resume
from track.storage import bootstrap_storage, connection


def write_resume(path: Path, text: str = "resume") -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def seed_role_applications(database_path: Path, resume_file: Path, count: int) -> None:
    add_resume("base", str(resume_file), database_path)
    for index in range(count):
        add_application(f"Role {index}", "base", database_path)


@pytest.fixture
def isolated_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def database_path(isolated_home):
    return bootstrap_storage()


@pytest.fixture
def resume_file(isolated_home):
    return write_resume(isolated_home / "resume.pdf")


@pytest.fixture
def cli_runner(isolated_home):
    return CliRunner(env={"HOME": str(isolated_home)})


@pytest.fixture
def seed_resume(database_path, resume_file):
    def _seed(nickname: str = "base") -> int:
        return add_resume(nickname, str(resume_file), database_path)

    return _seed


@pytest.fixture
def seeded_application(database_path, seed_resume):
    seed_resume()
    app_id = add_application("Acme SWE Intern", "base", database_path)
    return database_path, app_id


@pytest.fixture
def seed_role_apps(database_path, resume_file):
    def _seed(count: int) -> None:
        seed_role_applications(database_path, resume_file, count)

    return _seed


@pytest.fixture
def seeded_filtered_applications(database_path, resume_file):
    add_resume("base", str(resume_file), database_path)
    add_resume("alt", str(resume_file), database_path)

    today = date.today()
    earlier = (today - timedelta(days=5)).isoformat()
    later = (today - timedelta(days=1)).isoformat()

    add_application("Older Role", "base", database_path)
    add_application("Newer Role", "alt", database_path)

    with connection(database_path) as conn:
        conn.execute(
            "UPDATE applications SET applied_date = ?, status = ? WHERE role_text = ?",
            (earlier, "ghost", "Older Role"),
        )
        conn.execute(
            "UPDATE applications SET applied_date = ?, status = ? WHERE role_text = ?",
            (later, "interviewing", "Newer Role"),
        )
        conn.commit()

    return database_path, earlier, later
