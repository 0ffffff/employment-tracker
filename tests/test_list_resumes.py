import json

from track.cli import main
from track.resumes import add_resume, list_resume_rows


def test_list_resume_orders_by_created_at_then_id_desc(database_path, resume_file):
    first_id = add_resume("older", str(resume_file), database_path)
    second_id = add_resume("newer", str(resume_file), database_path)

    rows = list_resume_rows(database_path)
    assert [row["id"] for row in rows] == [second_id, first_id]
    assert rows[0]["nickname"] == "newer"
    assert rows[0]["is_latest"] is True
    assert rows[1]["is_latest"] is False
    assert rows[0]["managed_path"].endswith(f"{second_id}.pdf")


def test_main_list_resume_json_output(resume_file, capsys):
    assert main(["add-resume", "base", str(resume_file)]) == 0
    capsys.readouterr()

    assert main(["list-resume", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["format_version"] == 1
    assert len(payload["resumes"]) == 1
    keys = set(payload["resumes"][0].keys())
    assert keys == {"id", "nickname", "managed_path", "is_latest", "created_at"}
    assert payload["resumes"][0]["nickname"] == "base"
    assert payload["resumes"][0]["is_latest"] is True


def test_main_list_resume_empty_db_json(database_path, capsys):
    assert main(["list-resume", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload == {"format_version": 1, "resumes": []}


def test_main_list_resume_human_empty(database_path, capsys):
    assert main(["list-resume"]) == 0
    assert capsys.readouterr().out.strip() == "No resumes found."


def test_main_list_resume_human_truncates_with_total(resume_file, capsys):
    for index in range(8):
        assert main(["add-resume", f"v{index}", str(resume_file)]) == 0
        capsys.readouterr()

    assert main(["list-resume"]) == 0
    out = capsys.readouterr().out
    assert out.count("\n") == 7
    assert "... 8 resumes total" in out
    assert "v7" in out
    assert "v3" in out
    assert "v2" not in out


def test_main_list_resume_all_shows_every_row(resume_file, capsys):
    for index in range(8):
        assert main(["add-resume", f"v{index}", str(resume_file)]) == 0
        capsys.readouterr()

    assert main(["list-resume", "--all"]) == 0
    out = capsys.readouterr().out
    assert "... 8 resumes total" not in out
    assert "v0" in out
    assert "v7" in out
