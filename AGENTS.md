# employment-tracker-2 — agent context

Greenfield rewrite of the **Track CLI** internship job-application tracker. Behavior and product intent are defined by the existing implementation in the sibling repo **`../employment-tracker`**.

## Required reading before implementing features

1. **[Source product reference](docs/reference/source-product-employment-tracker.md)** — full command surface, data model, business rules, error/confirmation behavior, out-of-scope items, and MVP checklist for this repo.
2. Original repo (read-only reference): `/Users/williamli/Developer/employment-tracker`

## Project goal

Replicate the source product as a **barebones** codebase that stays easy to extend (clear CLI / domain / storage layers, testable `database_path` injection, no premature frameworks). Defer analytics, cloud sync, and tab completion until core flows are solid unless explicitly requested.

## Python tooling

When this repo has a `pyproject.toml`, use **uv** for all Python workflows (`uv sync`, `uv run pytest`, `uv run track`, etc.), matching the source repo’s `AGENTS.md` policy.

## Commits

Create atomic commits per logical change; do not commit unless the user asks.

## Updating this doc

When replication diverges from v1 or new commands ship here, update `docs/reference/source-product-employment-tracker.md` (add a “v2 deltas” section) so future agents see one source of truth.
