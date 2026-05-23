# employment-tracker-2 — agent context

Greenfield rewrite of the **Track CLI** internship job-application tracker. Behavior and product intent are defined by the existing implementation in the sibling repo **`../employment-tracker`**.

## Required reading before implementing features

1. **[Source product reference](docs/reference/source-product-employment-tracker.md)** — command surface, data model, business rules, error/confirmation behavior, MVP checklist, and **v2 deltas**.
2. Original repo (read-only reference): `/Users/williamli/Developer/employment-tracker`

## Project goal

Replicate the source product as a **barebones** codebase: clear CLI / domain / storage layers, `database_path` injection in tests, no premature frameworks. Defer analytics, cloud sync, and **`track update` argument tab completion** until core flows are solid.

**Shipped in v2:** `add`, `add-resume`, `update`, `list`, `list-resume`; corrupt `track.db` recovery; subcommand-name completion via `install.sh` (Click `_TRACK_COMPLETE`); `add-resume` file-path completion via `click.Path`.

## Python tooling

Use **uv** for all Python workflows (`uv sync`, `uv run pytest`, `uv run track`, etc.).

## Commits

Create atomic commits per logical change; do not commit unless the user asks.

## Updating docs

When replication diverges from v1 or new commands ship, update `docs/reference/source-product-employment-tracker.md` (**v2 deltas** section).
