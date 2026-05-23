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

## Not yet implemented

From the v1 command surface: `track edit`, `track delete`, and `track remove-resume`. Shell tab completion is deferred until those core flows land (see `AGENTS.md`).

## Tests

```bash
uv run pytest
```
