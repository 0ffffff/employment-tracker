# Source product reference: `employment-tracker` (v1)

**Purpose:** This document captures the product built in the sibling repo [`employment-tracker`](file:///Users/williamli/Developer/employment-tracker) so agents working in **employment-tracker-2** can replicate behavior in a **barebones, scalable** form without re-reading the full source tree.

**Last reviewed:** 2026-05-23 (v1 reference repo; v2 implementation in this repository).

---

## Product summary

**Track CLI** is a **local-first terminal application** for tracking **internship job applications** and **resume versions**. Users never need a spreadsheet or cloud account: data lives under `~/.track/` as SQLite plus copied resume files.

| Attribute | Value |
|-----------|--------|
| Binary name | `track` |
| Python package | `employment-tracker` |
| Min Python | 3.12 |
| Primary dependency | `rapidfuzz` (fuzzy matching) |
| Optional dependency | None (shell tab completion uses Click built-in; no extra package) |
| Distribution | `uv tool install` / PyPI-oriented (`pyproject.toml` entry point) |

**Core user loop:**

1. Register resume copies with nicknames (`track add-resume`).
2. Log applications tied to a resume (`track add`).
3. Move applications through recruiting statuses (`track update`).
4. Inspect, correct, and clean up (`track list`, `track edit`, `track delete`, `track remove-resume`).

---

## Problem and design principles

From the original requirements brainstorm:

- Internship recruiting involves many repetitive applications, resume variants, and status updates that are easy to lose in notes or spreadsheets.
- **v1 intentionally barebones:** fast CLI, minimal commands, no analytics/charts/cloud.
- **Local-first:** `~/.track/` + SQLite; resume PDFs (etc.) are **copied** into managed storage, not referenced by original path only.
- **Safety over speed for mutations:** confirmation prompts by default; `-f` bypasses prompts; non-TTY without `-f` **fails fast** (no hanging on stdin).
- **Canonical identity:** numeric application IDs are source of truth; fuzzy role text is a convenience input.
- **Latest-resume default:** `track add` without `-r` uses the resume row marked `is_latest = 1`.

---

## On-disk layout

```
~/.track/
├── track.db          # SQLite (applications + resume metadata)
└── resumes/          # Managed copies of resume files ({id}{ext})
```

Bootstrap (`bootstrap_storage`) creates directories and applies `schema.sql` on first use. Corrupt non-database files at `track.db` are deleted and re-initialized.

---

## Data model

### `resumes`

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | Auto-increment |
| `nickname` | TEXT UNIQUE | User-facing name (e.g. `2027-default`) |
| `managed_path` | TEXT | Path under `~/.track/resumes/` |
| `is_latest` | INTEGER 0/1 | Exactly one row should be latest after successful `add-resume` |
| `created_at` | TEXT | ISO timestamp default |

### `applications`

| Column | Type | Notes |
|--------|------|--------|
| `id` | INTEGER PK | Stable identifier shown in CLI output |
| `role_text` | TEXT | Single free-form string: company + position (not split in v1) |
| `resume_id` | INTEGER FK → `resumes.id` | Required |
| `applied_date` | TEXT | `YYYY-MM-DD`; default **today** on `track add` |
| `status` | TEXT | Canonical full name (see statuses below) |

Index: `idx_applications_role_text` on `role_text`.

Foreign keys enforced: `PRAGMA foreign_keys = ON`.

---

## Application statuses

User input accepts **full names or single-letter shorthands**. Stored value is always the **canonical** string.

| Canonical | Aliases |
|-----------|---------|
| `ghost` | `g` |
| `reject` | `r` |
| `interviewing` | `i` |
| `offer` | `o` |
| `accepted` | `a` |

**Default on create:** `ghost` (application logged but no employer response yet).

---

## CLI command surface (complete)

| Command | Purpose |
|---------|---------|
| `track add <company_and_position> [-r resume_ref]` | Create application |
| `track add-resume <nickname> <path_to_file>` | Copy resume, mark latest |
| `track update <identifier> <status> [-f]` | Change status only |
| `track list [--json] [--status] [--applied-from] [--applied-to]` | List/filter applications |
| `track list-resume [--json] [--all]` | List registered resume copies |
| `track edit <identifier> [--role] [--applied-date] [--resume] [-f]` | Edit non-status fields |
| `track delete <identifier> [-f]` | Hard-delete application |
| `track remove-resume <nickname> [-f] [--repoint-to-latest]` | Delete resume row + file |

`<identifier>` for application commands: **numeric ID** (if string is all digits) **or** fuzzy match on `role_text`.

`<nickname>` for `remove-resume`: **exact** nickname match only (no fuzzy).

### `track add`

- Normalizes role text (collapse whitespace; reject empty).
- Resolves resume: `-r` → nickname lookup; else latest resume; else error with actionable message.
- Sets `applied_date` = local today, `status` = `ghost`.
- Prints: `Added application #<id>.`

### `track add-resume`

- Validates source file exists and is a file.
- Copies to temp file in `resumes/`, inserts DB row with `is_latest = 1`, clears previous latest, renames file to `{id}{extension}`.
- On nickname collision (`UNIQUE`): rollback temp file, `ValidationError`.
- On failure after insert: attempts cleanup (delete row, restore previous latest, remove files).

### `track update`

- Resolves application (ID or fuzzy).
- Normalizes status via alias table.
- Unless `-f`: TTY → `Confirm [y/N]` showing old/new status; non-TTY → `NonInteractiveError`.
- Prints: `Updated application #<id> to status '<canonical>'.`

### `track list`

- Bootstraps storage (empty DB → empty list).
- Filters: status (same tokens as update), `applied_from` / `applied_to` (inclusive `YYYY-MM-DD`).
- Sort: `applied_date DESC`, `id DESC`.
- Human table: ID, Applied, Status, Resume nickname, Role (truncated ~48 chars).
- `--json`: `{"format_version": 1, "applications": [...]}` with keys `id`, `role_text`, `status`, `applied_date`, `resume_nickname`.

**v2 human list preview:** By default, human output shows the **5 most recent** rows (same sort as full list), then a trailing line `... N applications total` when more rows match. Use `--all` for the full table. JSON is always complete.

### `track list-resume` (v2 only)

- Bootstraps storage (empty DB → empty list).
- Sort: `created_at DESC`, `id DESC`.
- Human table: ID, Added (`created_at`), Latest (`yes` when `is_latest`), Nickname, Path (`managed_path`, truncated ~48 chars).
- Same preview rule as `track list`: default **5** rows + `... N resumes total`; `--all` for full table.
- `--json`: `{"format_version": 1, "resumes": [...]}` with keys `id`, `nickname`, `managed_path`, `is_latest` (boolean), `created_at`.

### `track edit`

- Requires at least one of `--role`, `--applied-date`, `--resume`.
- Same identifier resolution as `update`.
- Shows field-level before/after on confirm; `No changes detected.` if noop.
- **Does not** change status (by design — use `update`).

### `track delete`

- Always prints impact preview (ID, role, status, applied, resume).
- Confirmation: user must type exact application id (stronger than y/N).
- Preview runs even with `-f`; `-f` only skips prompt.

### `track remove-resume`

- Cannot remove the **only** resume in the system.
- If applications reference the resume and `--repoint-to-latest` is **not** set: preview + error (must repoint explicitly).
- With `--repoint-to-latest`: repoint all referencing apps to **successor** resume = max(`created_at`), tie-break max(`id`), excluding target; if target was latest, promote successor to latest.
- If target is latest but unreferenced: still picks successor and promotes.
- DB transaction first; then `unlink` managed file (DB wins if file delete fails — user told to clean orphan manually).
- Confirmation: user must type exact nickname.

---

## Fuzzy matching (application identifier)

- Library: **RapidFuzz** `process.extract` with `fuzz.WRatio`.
- **Threshold:** score ≥ **85** or no match.
- **Multiple matches above threshold:** interactive numbered menu (TTY only); non-TTY → `NonInteractiveError` with hint to use ID.
- **Numeric identifier:** if stripped input is all digits, resolve by ID first (validates existence).

Tab completion reuses threshold 85 for role text; caps fuzzy completion candidates at **50**, sorted by score desc then id desc. Read-only DB access via `file:…?mode=ro` URI.

---

## Error model

All user-facing failures inherit `TrackError` and print to stderr; exit code `1`.

| Class | When |
|-------|------|
| `ValidationError` | Bad input, business rule violation |
| `NotFoundError` | Missing application, resume, or file |
| `NonInteractiveError` | Confirmation/disambiguation needed but not TTY and no `-f` |
| `CancelledError` | User declined confirmation |

---

## Source code module map (v1)

Useful when porting or simplifying:

| Module | Responsibility |
|--------|----------------|
| `track/cli.py` | Click group, dispatch, human/JSON list formatting |
| `track/applications.py` | Application CRUD, status normalization, list filters, fuzzy resolve |
| `track/resumes.py` | Resume copy/register, remove with repoint logic |
| `track/storage.py` | SQLite connection, schema init, bootstrap |
| `track/schema.sql` | DDL |
| `track/paths.py` | `~/.track` paths |
| `track/fuzzy.py` | RapidFuzz wrapper |
| `track/confirm.py` | Prompts, previews, candidate picker |
| `track/completion_data.py` | Read-only completion queries |
| `track/errors.py` | Exception types |

**Test coverage:** pytest suite per command (add, list, update fuzzy/id, edit, delete, remove-resume, storage bootstrap, completion). Tests inject `database_path` via temp dirs (see individual test files).

---

## Explicitly out of scope (v1) — do not replicate unless asked

From `docs/TODOS.md` in source repo:

- Analytics: counts by status, conversion rates, trends, charts
- Cloud sync / multi-device
- Full backup/restore (export/import including resume files) — partial: `list --json` only
- External integrations (spreadsheets, etc.)
- Undo / audit log for edits and deletes
- Bulk operations beyond `--repoint-to-latest`

---

## Evolution timeline (context only)

1. **Foundation (v1):** `add`, `add-resume`, `update` only — per `docs/brainstorms/2026-04-13-internship-cli-job-tracker-requirements.md`.
2. **vNext ops:** `list` (+ filters + JSON), `edit`, `delete`, `remove-resume`.
3. **Tab completion:** optional Click completion for `track update` IDs/statuses (v2); v1 also completed resume paths and other commands.

employment-tracker-2 should treat the **current** command set and rules above as the functional baseline.

---

## Guidance for employment-tracker-2 (barebones + scalable)

### Preserve (behavioral contract)

- Local-first `~/.track/` storage model and two-table schema (or compatible evolution).
- Command semantics and defaults listed in this doc (especially ghost default, latest resume, fuzzy threshold 85, confirmation/`-f`/non-TTY rules).
- Separation of **status updates** (`update`) vs **field edits** (`edit`).
- Deterministic successor resume rule on `remove-resume --repoint-to-latest`.

### Safe to defer in v2 initial build

- Shell tab completion for `track update` arguments (Click `shell_complete`) — optional; CLI must work without it.
- `TRACK_DEBUG_COMPLETION` and read-only URI completion paths.
- PyPI packaging polish — a minimal `pyproject.toml` + `uv run track` is enough to start.

### Scalability seams (recommended for v2 architecture)

Keep the v1 **module boundaries** even if code is smaller:

1. **CLI layer** — parsing and stdout only; no SQL in `cli.py`.
2. **Domain layer** — `applications` / `resumes` functions accepting `database_path: Path` (enables tests without touching `~/.track`).
3. **Storage layer** — connection + migrations; schema as SQL file or versioned migrations when schema grows.
4. **Ports later** — JSON list output already defines `format_version`; new exporters/importers can hang off the same row dicts without changing CLI verbs.

Avoid premature abstractions (repository interfaces, plugin systems) until a second storage backend or API is required.

### Minimal v2 MVP checklist

- [x] `bootstrap_storage` + schema (+ corrupt `track.db` recovery)
- [x] `add-resume`, `add`, `update` with tests
- [x] `list` (human + `--json`) and `list-resume`
- [x] Shared fuzzy resolve + confirmation helpers
- [ ] Then: `edit`, `delete`, `remove-resume`
- [ ] `track update` argument tab completion (deferred per `AGENTS.md` until core flows solid)
- [x] Subcommand name tab completion via `install.sh` (Click `_TRACK_COMPLETE`)
- [x] `add-resume` file-path tab completion via `click.Path`

### v2 deltas (employment-tracker-2)

| Area | v2 behavior |
|------|----------------|
| Package layout | `src/track/` (hatch wheel) |
| Dependencies | `click`, `rapidfuzz` required (no optional completion extra) |
| CLI framework | Click (`@click.group` + subcommands); entry point `track.cli:main` |
| Subcommand aliases | `ls`→`list`, `a`→`add`, `ar`→`add-resume`, `lr`→`list-resume`, `u`→`update`; hidden from `--help` and tab completion |
| `track update` identifier | Numeric ID or fuzzy `role_text` (threshold 85) |
| Commands not yet ported | `edit`, `delete`, `remove-resume` |
| Corrupt DB recovery | Reimplemented: non-SQLite `track.db` is deleted and re-initialized on bootstrap |
| Shell tab completion | Subcommand names (`install.sh`); `add-resume` path via `click.Path`; **`track update` ID/status deferred** |
| `track list` human output | Preview of 5 newest rows + `... N applications total`; `--all` for full table |
| `list-resume` | Lists managed resume copies (`list-resume [--json] [--all]`) with same preview rule as `list` |
| Code size | ~625 LOC across `src/track/*.py` (lean modules; shared list formatter in CLI) |
| Install | [0ffffff.github.io/install.sh](https://0ffffff.github.io/install.sh) one-liner (GitHub Pages); clones `0ffffff/employment-tracker`, `uv tool install`, PATH, optional subcommand tab completion |

---

### Reference paths

| Artifact | Path in source repo |
|----------|---------------------|
| User-facing README | `README.md` |
| Requirements brainstorm | `docs/brainstorms/2026-04-13-internship-cli-job-tracker-requirements.md` |
| Foundation plan | `docs/plans/2026-04-13-001-feat-track-cli-foundation-plan.md` |
| Ops expansion plan | `docs/plans/2026-04-13-002-feat-track-cli-vnext-ops-plan.md` |
| Tab completion plan | `docs/plans/2026-04-13-003-feat-track-cli-tab-completion-plan.md` |
| Future ideas | `docs/TODOS.md` |

---

## Example sessions

```bash
# First-time setup
track add-resume "2027-default" "./resume.pdf"
track add "Acme SWE Intern"
track update 1 interviewing

# Fuzzy update (interactive disambiguation if multiple matches)
track update "Acme SWE" i

# Scripting (non-TTY)
track update "Acme SWE Intern" i -f

# Inspect
track list --status i --applied-from 2026-01-01
track list --json

# Corrections and cleanup
track edit 1 --role "Acme SWE Intern (updated)"
track delete 1 -f
track remove-resume "old-version" --repoint-to-latest -f
```
