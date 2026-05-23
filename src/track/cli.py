import json
import sys

import click

from track.applications import (
    add_application,
    list_application_rows,
    update_application_status,
)
from track.errors import TrackError
from track.resumes import add_resume, list_resume_rows
from track.storage import bootstrap_storage

# Default human list preview length (matches pandas DataFrame.head() default).
LIST_HEAD_ROWS = 5


@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.pass_context
def cli(ctx: click.Context) -> int | None:
    """Track internship applications from your terminal."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return 1
    return None


@cli.command("add")
@click.argument("company_and_position")
@click.option(
    "-r",
    "--resume-ref",
    default=None,
    help="Resume nickname to associate.",
)
def add_cmd(company_and_position: str, resume_ref: str | None) -> None:
    """Add a new application."""
    database_path = bootstrap_storage()
    application_id = add_application(
        role_text=company_and_position,
        resume_ref=resume_ref,
        database_path=database_path,
    )
    click.echo(f"Added application #{application_id}.")


@cli.command("add-resume")
@click.argument("resume_reference_name")
@click.argument("path_to_resume")
def add_resume_cmd(resume_reference_name: str, path_to_resume: str) -> None:
    """Register a new resume and mark it latest."""
    database_path = bootstrap_storage()
    resume_id = add_resume(
        nickname=resume_reference_name,
        source_path=path_to_resume,
        database_path=database_path,
    )
    click.echo(f"Registered resume #{resume_id} as latest.")


@cli.command("update")
@click.argument("identifier")
@click.argument("status_or_option")
@click.option("-f", "--force", is_flag=True, help="Bypass confirmation prompt.")
def update_cmd(identifier: str, status_or_option: str, force: bool) -> None:
    """Update application status by ID or fuzzy role text match."""
    database_path = bootstrap_storage()
    application_id, status = update_application_status(
        identifier=identifier,
        raw_status=status_or_option,
        database_path=database_path,
        force=force,
        is_tty=_is_tty(),
    )
    click.echo(f"Updated application #{application_id} to status '{status}'.")


@cli.command("list")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option(
    "--status",
    "status_filter",
    default=None,
    help="Filter by status token (same as track update).",
)
@click.option(
    "--applied-from",
    default=None,
    help="Inclusive lower bound for applied_date (YYYY-MM-DD).",
)
@click.option(
    "--applied-to",
    default=None,
    help="Inclusive upper bound for applied_date (YYYY-MM-DD).",
)
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Show every matching application (default shows a short preview).",
)
def list_cmd(
    as_json: bool,
    status_filter: str | None,
    applied_from: str | None,
    applied_to: str | None,
    show_all: bool,
) -> None:
    """List applications with optional filters."""
    database_path = bootstrap_storage()
    rows = list_application_rows(
        database_path,
        status_filter=status_filter,
        applied_from=applied_from,
        applied_to=applied_to,
    )
    if as_json:
        click.echo(json.dumps({"format_version": 1, "applications": rows}, sort_keys=True))
        return
    _format_list_human(rows, show_all=show_all)


@cli.command("list-resume")
@click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON.")
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Show every resume (default shows a short preview).",
)
def list_resume_cmd(as_json: bool, show_all: bool) -> None:
    """List registered resume copies."""
    database_path = bootstrap_storage()
    rows = list_resume_rows(database_path)
    if as_json:
        click.echo(json.dumps({"format_version": 1, "resumes": rows}, sort_keys=True))
        return
    _format_list_resume_human(rows, show_all=show_all)


def _is_tty() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _format_list_human(rows: list[dict], *, show_all: bool = False) -> None:
    if not rows:
        click.echo("No applications found.")
        return

    total = len(rows)
    preview = rows if show_all or total <= LIST_HEAD_ROWS else rows[:LIST_HEAD_ROWS]

    click.echo(f"{'ID':<6} {'Applied':<12} {'Status':<14} {'Resume':<16} Role")
    for row in preview:
        role = str(row["role_text"])
        display_role = role if len(role) <= 48 else f"{role[:45]}..."
        click.echo(
            f"{int(row['id']):<6} {row['applied_date']:<12} {row['status']:<14} "
            f"{row['resume_nickname']:<16} {display_role}"
        )
    if not show_all and total > LIST_HEAD_ROWS:
        click.echo(f"... {total} applications total")


def _format_list_resume_human(rows: list[dict], *, show_all: bool = False) -> None:
    if not rows:
        click.echo("No resumes found.")
        return

    total = len(rows)
    preview = rows if show_all or total <= LIST_HEAD_ROWS else rows[:LIST_HEAD_ROWS]

    click.echo(f"{'ID':<6} {'Added':<20} {'Latest':<8} {'Nickname':<16} Path")
    for row in preview:
        path = str(row["managed_path"])
        display_path = path if len(path) <= 48 else f"{path[:45]}..."
        latest = "yes" if row["is_latest"] else ""
        click.echo(
            f"{int(row['id']):<6} {row['created_at']:<20} {latest:<8} "
            f"{row['nickname']:<16} {display_path}"
        )
    if not show_all and total > LIST_HEAD_ROWS:
        click.echo(f"... {total} resumes total")


def main(argv: list[str] | None = None) -> int:
    try:
        code = cli.main(args=argv, prog_name="track", standalone_mode=False)
        return 0 if code is None else int(code)
    except TrackError as exc:
        click.echo(str(exc), err=True)
        return 1
    except click.Abort:
        return 1
    except click.ClickException as exc:
        exc.show()
        return exc.exit_code
