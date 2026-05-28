---
title: "feat: Set an existing resume as latest"
type: feat
status: active
date: 2026-05-27
---

# feat: Set an existing resume as latest

## Summary

Add a dedicated CLI command to mark an existing resume as the system latest without uploading a new file. The feature keeps current `track add` behavior intact while giving users explicit control over which stored resume is used by default.

---

## Problem Frame

Today, `is_latest` only changes when users run `track add-resume`, which forces a new file registration even when they only want to switch the default to an existing resume. This creates unnecessary resume copies and friction in day-to-day application tracking.

---

## Requirements

- R1. Users can set an existing resume as latest from the CLI.
- R2. Latest selection works by resume nickname (consistent with existing resume reference semantics).
- R3. Exactly one resume remains latest after the command succeeds.
- R4. Unknown nickname returns a clear `NotFoundError` without data mutation.
- R5. `track add` without `-r` uses the newly selected latest resume.
- R6. Existing commands and JSON output contracts remain unchanged.
- R7. CLI wiring for this command follows patterns that make future argument tab-completion and fuzzy candidate support easy to add in a dedicated completion iteration.

---

## Scope Boundaries

- No resume edit or delete functionality in this plan.
- No schema redesign or migration to enforce a DB-level unique-latest constraint.
- No changes to application status flows, fuzzy update behavior, or listing formats.
- No implementation of argument tab-completion/fuzzy-completion in this iteration (planned follow-up alongside `update` argument completion).

### Deferred to Follow-Up Work

- Add optional ID-based selection (`set-latest-resume <id>`) if users request it.
- Consider a reusable helper for resume selection flows when remove/edit commands are added.
- Add argument tab-completion + fuzzy candidate completion for argument-bearing commands (including `set-latest-resume`) in the planned completion iteration.

---

## Context & Research

### Relevant Code and Patterns

- `src/track/resumes.py`: existing `add_resume()` already clears prior latest and sets a new latest.
- `src/track/applications.py`: `_resume_for_add()` resolves latest when `-r` is omitted.
- `src/track/cli.py`: command registration, alias handling, and one-line success messaging pattern.
- `src/track/schema.sql`: `resumes.is_latest` boolean-like flag with `CHECK`.
- `tests/test_add_resume.py`, `tests/test_add_application.py`, `tests/test_cli_integration.py`, `tests/test_list_resumes.py`: patterns to extend.

### Institutional Learnings

- No `docs/solutions/` corpus exists in this repository today.
- `docs/reference/source-product-employment-tracker.md` emphasizes latest-resume default semantics and preserving lean command-specific behavior.

### External References

- Not required for this plan; local patterns are strong and the feature is low-risk, internal CLI behavior.

---

## Key Technical Decisions

- Add a new explicit command: `track set-latest-resume <resume_ref_name>`.
  - Rationale: clear intent, minimal coupling, no behavior changes to existing commands.
- Resolve target resume by exact nickname (same style as `add -r` reference lookup).
  - Rationale: predictable and already familiar to users.
- Implement latest switch in a domain function in `resumes.py`, called by CLI.
  - Rationale: preserve CLI/domain separation and testability.
- Keep operation idempotent if target is already latest.
  - Rationale: avoids surprising failures and keeps command safe to rerun.
- Add alias `slr` in `_SUBCOMMAND_ALIASES` using existing alias patterns.
  - Rationale: matches project shorthand conventions and requested ergonomics.
- Keep CLI argument handling encapsulated in a narrow command wrapper so future `shell_complete` integration can be added without touching domain logic.
  - Rationale: aligns with upcoming completion iteration across argument-bearing commands.

---

## Open Questions

### Resolved During Planning

- Should this be implicit in `list-resume` or a dedicated command? Dedicated command.
- Should nickname or fuzzy matching be used? Exact nickname only for now.

### Deferred to Implementation

- Exact success message wording for idempotent case (reuse general success message vs explicit "already latest").

---

## Implementation Units

- U1. **Add domain operation to switch latest resume**

**Goal:** Introduce a single domain function that marks one existing resume as latest.

**Requirements:** R2, R3, R4

**Dependencies:** None

**Files:**
- Modify: `src/track/resumes.py`
- Test: `tests/test_add_resume.py`

**Approach:**
- Add `set_latest_resume(nickname: str, database_path: Path) -> int`.
- Query target by nickname; raise `NotFoundError` if missing.
- In one transaction:
  - clear current latest (`UPDATE resumes SET is_latest = 0 WHERE is_latest = 1`)
  - set target latest (`UPDATE resumes SET is_latest = 1 WHERE id = ?`)
- Return target resume ID for CLI messaging.

**Patterns to follow:**
- `add_resume()` transaction/update style in `src/track/resumes.py`.
- Existing `NotFoundError` usage patterns across domain modules.

**Test scenarios:**
- Happy path: switching from A to B sets B latest and unsets A.
- Happy path: only one row has `is_latest = 1` after switching.
- Edge case: target already latest keeps invariant and succeeds.
- Error path: unknown nickname raises `NotFoundError` and latest row is unchanged.

**Verification:**
- Domain tests pass and DB assertions confirm exactly one latest resume.

---

- U2. **Expose command in CLI**

**Goal:** Add user-facing command to invoke latest-switch behavior.

**Requirements:** R1, R2, R6, R7

**Dependencies:** U1

**Files:**
- Modify: `src/track/cli.py`
- Test: `tests/test_cli_integration.py`

**Approach:**
- Register `set-latest-resume` command with one nickname argument.
- Call `set_latest_resume()` and print a one-line success message.
- Add `slr` alias in `_SUBCOMMAND_ALIASES`, matching current alias declaration style.
- Keep command wrapper thin and self-contained so `shell_complete` can be attached to the argument in the later completion-focused iteration.

**Patterns to follow:**
- Existing command wrappers `add-resume`, `update`, and alias mapping in `src/track/cli.py`.

**Test scenarios:**
- Happy path: command exits `0` and prints success message for existing nickname.
- Happy path: alias `slr` executes the same behavior as `set-latest-resume`.
- Error path: unknown nickname exits non-zero and prints clear error message.
- Integration: command appears in help and does not alter existing command behavior.

**Verification:**
- CLI integration tests pass for both success and failure flows.

---

- U3. **Validate downstream behavior and docs**

**Goal:** Ensure newly selected latest resume is used by application creation and documented.

**Requirements:** R5, R6

**Dependencies:** U1, U2

**Files:**
- Modify: `tests/test_add_application.py`
- Modify: `README.md`

**Approach:**
- Extend application add test to:
  - create two resumes
  - switch latest to the older/non-current one
  - add application without `-r`
  - assert linked `resume_id`/nickname matches switched latest
- Document command in README usage examples and behavior notes.

**Patterns to follow:**
- Existing `test_add_without_resume_ref_uses_latest` pattern in `tests/test_add_application.py`.
- README command section style.

**Test scenarios:**
- Covers R5: add without `-r` after latest switch uses newly selected resume.
- Edge case: repeated switch commands still preserve `track add` default selection correctness.
- Test expectation: none for docs change itself.

**Verification:**
- Behavior tests prove latest selection affects `track add` default resolution.
- README includes accurate example and command description.

---

## System-Wide Impact

- **Interaction graph:** new CLI command -> `resumes.py` mutation -> existing `applications.py` latest lookup.
- **Error propagation:** `NotFoundError` bubbles through existing `TrackError` handling path.
- **State lifecycle risks:** potential multi-latest inconsistency is controlled by transaction and explicit two-step update.
- **API surface parity:** no JSON schema or existing command signature changes.
- **Unchanged invariants:** latest resume remains the default for `track add` when `-r` is omitted.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Command succeeds but leaves invalid latest state | Transaction + tests asserting exactly one latest row |
| Nickname mismatch causes user confusion | Keep exact-match error message actionable and consistent with existing resume-ref errors |
| Alias churn harms discoverability | Keep full command name documented and ensure alias coverage in CLI integration tests |

---

## Documentation / Operational Notes

- Update README command examples to include switching latest resume.
- No migration or install script changes required.

---

## Sources & References

- Related code: `src/track/resumes.py`, `src/track/cli.py`, `src/track/applications.py`
- Related tests: `tests/test_add_resume.py`, `tests/test_add_application.py`, `tests/test_cli_integration.py`
- Product behavior reference: `docs/reference/source-product-employment-tracker.md`
