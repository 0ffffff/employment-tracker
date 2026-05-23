# Track CLI (v2)

Local-first CLI for internship job applications and resume versions. Data lives under `~/.track/` (SQLite + copied resume files).

Full behavior contract: [source product reference](docs/reference/source-product-employment-tracker.md) (see **v2 deltas** for intentional differences from v1).

## Architecture

```
src/track/
├── cli.py           # Click commands, human/JSON output
├── applications.py  # Applications: add, list, update, fuzzy resolve
├── resumes.py       # Resumes: add-resume, list-resume
├── storage.py       # SQLite connection + bootstrap
├── schema.sql       # DDL
├── paths.py         # ~/.track paths
├── fuzzy.py         # RapidFuzz WRatio (threshold 85)
├── confirm.py       # Prompts + disambiguation
└── errors.py        # TrackError hierarchy
```

Domain code takes `database_path: Path` for tests; the CLI calls `bootstrap_storage()` then passes that path through.

## Install

Requires **Python 3.12+** and [uv](https://docs.astral.sh/uv/).

| Method | Command |
|--------|---------|
| Install script (recommended) | `./install.sh` from a clone |
| Manual | `uv tool install . && uv tool update-shell` |
| PyPI (when published) | `uv tool install employment-tracker` |

**Pipe install** (set your repo URL):

```bash
export TRACK_INSTALL_REPO="https://github.com/OWNER/employment-tracker-2.git"
curl -fsSL "${TRACK_INSTALL_REPO%/git}/raw/main/install.sh" | bash
```

If `track` is not found: `uv tool update-shell`, then open a new terminal.

```bash
uv tool upgrade employment-tracker   # upgrade
uv tool uninstall employment-tracker # remove
```

### Tab completion (optional)

`install.sh` adds Click completion to `~/.bashrc` or `~/.zshrc` for **subcommand names** only. It does not complete `track update` IDs or status tokens.

```bash
eval "$(_TRACK_COMPLETE=zsh_source track)"    # zsh
eval "$(_TRACK_COMPLETE=bash_source track)"   # bash 4.4+
TRACK_INSTALL_SKIP_COMPLETION=1 ./install.sh  # skip during install
```

## Usage

First run creates `~/.track/` automatically.

```bash
# Resumes
track add-resume "2027-default" ./resume.pdf
# → Registered resume #1 as latest.

# Applications (latest resume if -r omitted; status ghost; applied_date today)
track add "Acme SWE Intern"
track add "Globex Data Intern" -r "2027-default"

# Status update (ID or fuzzy role_text ≥85; confirm unless -f)
track update 1 interviewing
track update "Acme SWE Intern" i -f

# Lists (human: 5-row preview; --all for full table; JSON: full set)
track list
track list --json --status i
track list-resume --json --all
```

**Status tokens:** `ghost`/`g`, `reject`/`r`, `interviewing`/`i`, `offer`/`o`, `accepted`/`a`.

Example human list output:

```
ID     Applied      Status         Resume           Role
1      2026-05-23   interviewing   2027-default     Acme SWE Intern
... 1 applications total
```

Example JSON (`sort_keys` puts `format_version` first):

```json
{"applications": [], "format_version": 1}
```

## Not in v2 yet

`track edit`, `track delete`, `track remove-resume`, and tab completion for `track update` arguments. See `docs/plans/2026-05-23-001-feat-track-update-tab-completion-plan.md`.

## Development

```bash
uv sync
uv run track --help
uv run pytest
```
