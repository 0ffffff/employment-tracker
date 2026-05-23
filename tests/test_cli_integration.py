import json

from click.testing import CliRunner

from track.cli import cli, main


def test_cli_recognizes_core_subcommands(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner(env={"HOME": str(tmp_path)})
    resume = tmp_path / "resume.pdf"
    resume.write_text("pdf-bytes", encoding="utf-8")

    runner.invoke(cli, ["add-resume", "default", str(resume)])
    add_result = runner.invoke(cli, ["add", "Acme SWE Intern", "-r", "default"])
    assert add_result.exit_code == 0
    assert add_result.output.strip() == "Added application #1."

    list_result = runner.invoke(
        cli,
        ["list", "--json", "--status", "i", "--applied-from", "2026-01-01"],
    )
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output.strip())
    assert payload == {"applications": [], "format_version": 1}

    list_resume_result = runner.invoke(cli, ["list-resume", "--json", "--all"])
    assert list_resume_result.exit_code == 0
    resume_payload = json.loads(list_resume_result.output.strip())
    assert resume_payload["format_version"] == 1
    assert len(resume_payload["resumes"]) == 1
    assert resume_payload["resumes"][0]["nickname"] == "default"


def test_main_without_subcommand_returns_non_zero():
    assert main([]) == 1


def test_main_list_empty_db_json(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--json"], env={"HOME": str(tmp_path)})
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    assert payload == {"applications": [], "format_version": 1}


def test_end_to_end_add_resume_add_list_update(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner(env={"HOME": str(tmp_path)})
    resume = tmp_path / "resume.pdf"
    resume.write_text("pdf-bytes", encoding="utf-8")

    add_resume_result = runner.invoke(
        cli, ["add-resume", "2027-default", str(resume)]
    )
    assert add_resume_result.exit_code == 0
    assert "Registered resume" in add_resume_result.output

    add_result = runner.invoke(cli, ["add", "Acme SWE Intern"])
    assert add_result.exit_code == 0
    assert "Added application #1." in add_result.output

    list_result = runner.invoke(cli, ["list"])
    assert list_result.exit_code == 0
    assert "Acme SWE Intern" in list_result.output
    assert "ghost" in list_result.output

    update_result = runner.invoke(cli, ["update", "1", "i", "-f"])
    assert update_result.exit_code == 0
    assert "interviewing" in update_result.output
