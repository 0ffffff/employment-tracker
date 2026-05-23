# Agent orchestration prompt: Track CLI shell tab completion (Click)

**Audience:** Agent lead coordinating subagents on `employment-tracker-2`.  
**Goal:** Ship optional shell tab completion for `track update` (application identifiers + status tokens) using **Click `shell_complete`**, reusing existing `completion_data.py`, with native multi-candidate Tab UX (`track update Amaz<TAB>` → list of matching `role_text` values).

**Authoritative product spec:** `docs/reference/source-product-employment-tracker.md`  
**Detailed engineering plan:** `docs/plans/2026-05-23-001-feat-track-update-tab-completion-plan.md` (note deltas below)  
**v1 reference implementation (read-only):** `/Users/williamli/Developer/employment-tracker/track/cli.py`, `track/completion_data.py`, `tests/test_completion_*.py`

---

## Mission outcome

When a user runs:

```bash
eval "$(track --install-completion zsh)"   # or bash
track update Amaz<TAB>
track update "Amaz<TAB>
track update 1<TAB>
track update 1 i<TAB>
```

they get:

1. **Application identifier completion** — numeric ID prefixes and fuzzy `role_text` matches from `~/.track/track.db`, up to **50** candidates, sorted by fuzzy score desc then id desc.
2. **Status completion** — keys from `STATUS_ALIASES` on the second positional.
3. **Native shell behavior** — one match fills the token; multiple matches list on double-Tab (shell handles display; completer returns all matches).
4. **Runtime parity** — a completed `role_text` is accepted by `track update` via existing `_resolve_application_id` (WRatio ≥ 85).
5. **No regressions** — `track` works without installing completion; normal commands unchanged.

---

## Frozen technical decisions (do not relitigate)

| Decision | Rationale |
|----------|-----------|
| **Click `shell_complete`**, not argcomplete, not Git-style bash scripts | CLI is Click; README already defers to Click shell completion. |
| **Reuse `completion_data.py`** as single source for DB-backed candidates | Already implements RO SQLite, SQL prefix + fuzzy, digit IDs, status keys. |
| **Complete to `role_text` strings** (not `#id`) for fuzzy path | Matches runtime `_resolve_application_id` and v1 behavior. |
| **Empty application prefix → `[]`** | Avoid flooding Tab on bare `track update <TAB>`. |
| **No `bootstrap_storage()` on Tab** | Use `db_path().is_file()` only; read-only completion path. |
| **SQL `LIKE prefix%` NOCASE prefilter, then fuzzy threshold 85** | Latency + v1 parity; document limitation: roles where the typed prefix is not a leading substring of `role_text` won't appear until user types more. |
| **Optional install only** | Core CLI must not require completion machinery at runtime. |

### Plan document deltas (2026-05-23)

The feat plan (`2026-05-23-001-...`) still mentions **argcomplete** in R7–R8. **Override:** implement **Click shell completion** only. v2 **already has** fuzzy runtime resolve in `applications._resolve_application_id`; do not re-implement unless tests prove a gap.

---

## Current codebase inventory (verify before coding)

| Artifact | Expected state | Action if missing |
|----------|----------------|-------------------|
| `src/track/completion_data.py` | `application_completion_candidates`, `status_completion_candidates`, RO URI, cap 50 | Implement per plan |
| `src/track/fuzzy.py` | `candidate_matches` WRatio ≥ threshold | Shared with runtime |
| `src/track/applications.py` | `_resolve_application_id` fuzzy + digit + TTY disambiguation | Must pass before shipping completion |
| `src/track/schema.sql` | `idx_applications_role_text_nocase` | Add + idempotent `CREATE INDEX IF NOT EXISTS` in init |
| `src/track/cli.py` | Click group; **no** `shell_complete` yet | Wire completers |
| `tests/test_completion_data.py` | Unit tests for candidate functions | Extend if API changes |
| `tests/test_completion_argcomplete.py` | **Skipped** (argcomplete removed) | **Replace** with Click completion tests |
| `pyproject.toml` | `argcomplete` in optional `completion` extra | **Remove** argcomplete; completion uses Click built-in |
| `README.md` | Says completion unavailable | Update install instructions |

---

## Workstreams (subagent assignments)

Assign one subagent per stream. Lead merges in dependency order.

### Wave 0 — Verification (read-only, parallel)

**Subagent: `verify-baseline`**

- Read `applications._resolve_application_id` and confirm fuzzy + digit behavior matches product reference.
- Run `uv run pytest tests/test_completion_data.py tests/test_cli_integration.py` (or full suite); report failures.
- Confirm NOCASE index exists in `schema.sql` and is created on bootstrap for fresh DB.
- Output: short status report (pass/fail + gaps). **No code changes** unless index migration is missing.

---

### Wave 1 — Core wiring (sequential dependency: verify passes)

**Subagent: `click-completers`**

**Files:** `src/track/cli.py` (primary), optionally `src/track/completion.py` if lead prefers a thin module.

**Tasks:**

1. Add completer functions:

   ```python
   def complete_application_identifier(ctx, param, incomplete) -> list[click.shell_completion.CompletionItem]:
       # Lazy-import completion_data + db_path
       # Return CompletionItem(text=role_text) for each candidate
       # Optional: help=f"#{id}" if you extend completion_data to return ids

   def complete_status_token(ctx, param, incomplete) -> list[click.shell_completion.CompletionItem]:
       # status_completion_candidates(incomplete)
   ```

2. Attach to `update` command:

   ```python
   @click.argument("identifier", shell_complete=complete_application_identifier)
   @click.argument("status_or_option", shell_complete=complete_status_token)
   ```

3. **Do not** call `bootstrap_storage()` inside completers.

4. Swallow errors in completers → `[]` (match v1 `_complete_application_ids` try/except pattern).

5. Keep `main()` / `cli` import graph lean: lazy-import heavy modules inside completers only.

**Acceptance:**

- `uv run track --install-completion bash` succeeds (or documented equivalent).
- Manual smoke: seeded DB, `track update Ama` + Tab returns Amazon role text.

---

**Subagent: `schema-index`** (parallel with click-completers if index missing)

**Files:** `src/track/schema.sql`, `src/track/storage.py` (init/migration)

**Tasks:**

1. Ensure `CREATE INDEX IF NOT EXISTS idx_applications_role_text_nocase ON applications(role_text COLLATE NOCASE)`.
2. Idempotent apply on existing user DBs during `init_db` / bootstrap.
3. Test: fresh DB has index in `sqlite_master`.

**Acceptance:** `test_completion_data` prefix queries remain fast; storage test documents index.

---

### Wave 2 — Tests (parallel after Wave 1 completers exist)

**Subagent: `tests-completion`**

**Files:** `tests/test_completion_click.py` (new), retire or rewrite `tests/test_completion_argcomplete.py`

**Tasks:**

1. **Keep** `tests/test_completion_data.py` — do not duplicate fuzzy/SQL logic in integration tests.

2. **Add Click shell completion integration tests** using Click’s completion entry point, e.g.:

   - Invoke completion for command `update`, argument index for `identifier`, `incomplete="Ama"`.
   - Assert `"Amazon SWE Intern"` in results (seed DB via `bootstrap_storage` + `add_application`).
   - Two-row fuzzy fixture: both Acme roles present for `incomplete="Acme"`.
   - Digit prefix: `incomplete="1"` returns id strings.
   - Status: `incomplete="i"` includes `interviewing`.
   - Quoted partial: `incomplete="Amaz"` (shell may pass without quote; test the completer input, not shell quoting).

   Consult Click docs for the supported test hook (`shell_complete` / `CliRunner` / env-based completion) for Click 8.1+.

3. **Remove or delete** skipped argcomplete tests once Click tests cover the same contracts.

4. Test: `main(["list", "--json"])` still works when completion is not invoked (no `_ARGCOMPLETE` side effects).

**Acceptance:** `uv run pytest tests/test_completion_data.py tests/test_completion_click.py` green.

---

### Wave 3 — Packaging & docs (after Wave 1)

**Subagent: `docs-packaging`**

**Files:** `pyproject.toml`, `README.md`, `docs/reference/source-product-employment-tracker.md` (v2 deltas section only)

**Tasks:**

1. **Remove `argcomplete`** from `[project.optional-dependencies] completion` and dev group unless another feature needs it. Click completion does not need argcomplete. If the `completion` extra becomes empty, remove the extra or document that completion is built-in with install script only.

2. **README** — replace “temporarily unavailable” with:

   ```bash
   # bash
   eval "$(track --install-completion bash)"
   # zsh
   eval "$(track --install-completion zsh)"
   ```

   Note: each Tab spawns a new Python process; first Tab may feel slower than DB work.

3. **Reference doc** — update v2 deltas: shell completion implemented via Click; identifier + status on `update`; link to install commands.

4. Optional: `TRACK_DEBUG_COMPLETION=1` → stderr logs from `completion_data` (already supported).

**Acceptance:** README instructions work on macOS zsh/bash; reference doc matches behavior.

---

## Explicit non-goals (defer to follow-up PR)

- Completion for `edit`, `delete`, `remove-resume`, `add -r`, `list --status`, `add-resume` paths
- Fish/tcsh-first-class support
- Completion daemon / long-lived process
- Broadening SQL prefilter beyond leading `role_text` prefix (middle-of-string fuzzy Tab)
- `CompletionItem.help` with scores (nice-to-have for Zsh, not required for MVP)

---

## Lead agent protocol

### Sequencing

```text
Wave 0 (verify-baseline) ──┬──► Wave 1 (click-completers) ──► Wave 2 (tests-completion)
                           └──► Wave 1 (schema-index)     ──┘
Wave 1 + 2 ──► Wave 3 (docs-packaging)
```

### Merge gates

Before marking the epic done:

- [ ] `uv run pytest` full suite green
- [ ] No `bootstrap_storage` in completion code paths (grep)
- [ ] Completed `role_text` from Tab runs through `track update` without error (manual or integration)
- [ ] README install section accurate
- [ ] Reference doc v2 deltas updated
- [ ] argcomplete removed or explicitly justified if kept for unrelated reason

### Subagent prompt template

When spawning a subagent, include:

```text
You are implementing workstream <ID> for employment-tracker-2 tab completion.
Read: docs/plans/prompt.md (this file), docs/plans/2026-05-23-001-feat-track-update-tab-completion-plan.md, docs/reference/source-product-employment-tracker.md
Use uv for all Python commands (uv run pytest, uv run track).
Do not use argcomplete; use Click shell_complete only.
Do not call bootstrap_storage in completers.
Match v1 behavior in ../employment-tracker for completion semantics.
Scope: only files listed in your workstream. Atomic commits per logical change if user requested commits.
Return: summary, files changed, test commands run + results, any blockers for lead.
```

### Conflict avoidance

| Stream | Owns |
|--------|------|
| `click-completers` | `cli.py`, new `completion.py` if any |
| `schema-index` | `schema.sql`, `storage.py` |
| `tests-completion` | `tests/test_completion_*.py` |
| `docs-packaging` | `README.md`, `pyproject.toml`, reference doc deltas |

Lead resolves overlaps in `cli.py` vs tests vs docs.

---

## Acceptance examples (end-to-end)

| Example | Expected |
|---------|----------|
| AE1 | DB has `"Amazon SWE Intern"`. `track update Ama` + Tab → candidate includes full role text. |
| AE2 | DB has ids 1, 10, 12. `track update 1` + Tab → `1`, `10`, `12` as offered completions where applicable. |
| AE3 | `track update 1 i` + Tab on status → `interviewing` (and alias keys starting with `i`). |
| AE4 | Two Acme applications. `track update Acme` + double Tab → both role texts listed. |
| AE5 | No `~/.track/track.db`. Tab on identifier → no DB candidates (empty or shell default). |
| AE6 | After Tab-completing role text, `track update "<completed>" interviewing` succeeds (same fuzzy path as typing). |

---

## Key implementation snippets (reference for subagents)

**Completer shape (Click 8):**

```python
def complete_application_identifier(
    ctx: click.Context,
    param: click.Parameter,
    incomplete: str,
) -> list[click.shell_completion.CompletionItem]:
    try:
        from track.completion_data import application_completion_candidates
        from track.paths import db_path

        path = db_path()
        if not path.is_file():
            return []
        return [
            click.shell_completion.CompletionItem(c)
            for c in application_completion_candidates(path, incomplete)
        ]
    except Exception:
        return []
```

**Candidate pipeline (already in `completion_data.py`):**

1. Missing DB file → `[]`
2. Empty/whitespace prefix → `[]`
3. All-digit prefix → digit id strings
4. Else `LIKE prefix%` NOCASE → `candidate_matches(..., 85)` → sort → cap 50 → `role_text` strings

**Runtime resolve (already in `applications.py`):** full-table fuzzy for execution; completion uses prefix prefilter for speed — document mismatch for non-prefix role text.

---

## Commands cheat sheet

```bash
uv sync
uv run pytest tests/test_completion_data.py -q
uv run pytest tests/test_completion_click.py -q   # after added
uv run pytest -q

# Manual completion install (after implementation)
eval "$(uv run track --install-completion zsh)"
uv run track add-resume base ./resume.pdf
uv run track add "Amazon SWE Intern"
uv run track update Ama<TAB>
```

---

## Definition of done

The epic is complete when all merge gates pass and a human can install shell completion, Tab-complete application identifiers (fuzzy `role_text` and numeric ids) and status tokens on `track update`, see multiple candidates when ambiguous, and run the completed command successfully without installing argcomplete.
