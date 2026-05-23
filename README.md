# employment-tracker (v2)

Local-first **Track CLI** for internship job applications and resume versions.

## Setup

```bash
uv sync
```

## Usage

```bash
uv run track add-resume "2027-default" ./resume.pdf
uv run track add "Acme SWE Intern"
uv run track update 1 interviewing
uv run track list
uv run track list --json --status i
uv run track list-resume
uv run track list-resume --json
```

Data is stored under `~/.track/` (SQLite + copied resume files).

`track update` accepts a numeric application ID or partial role text (fuzzy match, score ≥ 85).

## Shell tab completion (optional)

Tab completion for `track update` (application identifiers and status tokens) uses [Click shell completion](https://click.palletsprojects.com/en/stable/shell-completion/). Register completion for the **`track` executable** (not `uv`):

```bash
# After: uv tool install .
# bash — add to ~/.bashrc
eval "$(_TRACK_COMPLETE=bash_source track)"

# zsh — add to ~/.zshrc
eval "$(_TRACK_COMPLETE=zsh_source track)"
```

During local development without `uv tool install`, use the same pattern with the script on your PATH (for example `uv run track` only inside the eval, never `uv run track` as the command you type before Tab):

```bash
eval "$(_TRACK_COMPLETE=zsh_source $(which track))"
```

Open a **new shell** after editing rc files. Verify with `type _track_completion` (bash) or `which _track_completion` (zsh) — it should be defined.

Each Tab starts a new Python process, so the first completion may feel slower than the database work. Identifier completion matches leading-prefix role text in the database (not middle-of-string fuzzy); type more of the role name or use a numeric id if a match does not appear. Set `TRACK_DEBUG_COMPLETION=1` to log completion SQLite errors to stderr.

## Tests

```bash
uv run pytest
```
