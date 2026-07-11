import json

from track.cli import cli, main


def test_cli_recognizes_core_subcommands(cli_runner, resume_file):
    cli_runner.invoke(cli, ["add-resume", "default", str(resume_file)])
    add_result = cli_runner.invoke(cli, ["add", "Acme SWE Intern", "-r", "default"])
    assert add_result.exit_code == 0
    assert add_result.output.strip() == "Added application #1."

    list_result = cli_runner.invoke(
        cli,
        ["list", "--json", "--status", "i", "--applied-from", "2026-01-01"],
    )
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output.strip())
    assert payload == {"applications": [], "format_version": 1}

    list_resume_result = cli_runner.invoke(cli, ["list-resume", "--json", "--all"])
    assert list_resume_result.exit_code == 0
    resume_payload = json.loads(list_resume_result.output.strip())
    assert resume_payload["format_version"] == 1
    assert len(resume_payload["resumes"]) == 1
    assert resume_payload["resumes"][0]["nickname"] == "default"


def test_cli_subcommand_aliases(cli_runner, resume_file):
    assert cli_runner.invoke(cli, ["ar", "default", str(resume_file)]).exit_code == 0
    assert (
        cli_runner.invoke(cli, ["a", "Acme SWE Intern", "-r", "default"]).exit_code == 0
    )
    list_result = cli_runner.invoke(cli, ["ls", "--json"])
    assert list_result.exit_code == 0
    assert json.loads(list_result.output.strip())["applications"]
    list_resume_result = cli_runner.invoke(cli, ["lr", "--json"])
    assert list_resume_result.exit_code == 0
    assert json.loads(list_resume_result.output.strip())["resumes"]
    slr_result = cli_runner.invoke(cli, ["slr", "default"])
    assert slr_result.exit_code == 0
    assert "Set resume #1 as latest." in slr_result.output
    update_result = cli_runner.invoke(cli, ["u", "1", "i", "-f"])
    assert update_result.exit_code == 0
    assert "interviewing" in update_result.output

    assert cli_runner.invoke(cli, ["xyz"]).exit_code != 0


def test_main_without_subcommand_returns_non_zero():
    assert main([]) == 1


def test_main_list_empty_db_json(cli_runner):
    result = cli_runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    assert payload == {"applications": [], "format_version": 1}


def test_end_to_end_add_resume_add_list_update(cli_runner, resume_file):
    add_resume_result = cli_runner.invoke(
        cli, ["add-resume", "2027-default", str(resume_file)]
    )
    assert add_resume_result.exit_code == 0
    assert "Registered resume" in add_resume_result.output

    add_result = cli_runner.invoke(cli, ["add", "Acme SWE Intern"])
    assert add_result.exit_code == 0
    assert "Added application #1." in add_result.output

    list_result = cli_runner.invoke(cli, ["list"])
    assert list_result.exit_code == 0
    assert "Acme SWE Intern" in list_result.output
    assert "ghost" in list_result.output

    update_result = cli_runner.invoke(cli, ["update", "1", "i", "-f"])
    assert update_result.exit_code == 0
    assert "interviewing" in update_result.output


def test_set_latest_resume_switches_default_resume_for_add(cli_runner, resume_file):
    assert cli_runner.invoke(cli, ["add-resume", "first", str(resume_file)]).exit_code == 0
    assert cli_runner.invoke(cli, ["add-resume", "second", str(resume_file)]).exit_code == 0
    set_latest_result = cli_runner.invoke(cli, ["set-latest-resume", "first"])
    assert set_latest_result.exit_code == 0
    assert "Set resume #1 as latest." in set_latest_result.output

    assert cli_runner.invoke(cli, ["add", "Acme SWE Intern"]).exit_code == 0
    list_result = cli_runner.invoke(cli, ["list", "--json"])
    assert list_result.exit_code == 0
    payload = json.loads(list_result.output.strip())
    assert payload["applications"][0]["resume_nickname"] == "first"


def test_set_latest_resume_unknown_name_returns_error(cli_runner, resume_file):
    assert cli_runner.invoke(cli, ["add-resume", "default", str(resume_file)]).exit_code == 0

    result = cli_runner.invoke(cli, ["set-latest-resume", "missing"])
    assert result.exit_code == 1
    assert str(result.exception) == "Resume reference 'missing' was not found."
