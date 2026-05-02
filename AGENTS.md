# Huguenot Inn Agent Guidance

## Project Direction

- Preserve no-matter PDF bundle behavior before changing workflows.
- Use TDD for behavior changes: add characterization tests first, then refactor or extend.
- Keep GUI code thin. Domain rules, persistence, document rendering, and PDF bundling belong outside Tkinter callbacks.

## Architecture

- Expected layers:
  - `huguenot.domain`
  - `huguenot.application`
  - `huguenot.persistence`
  - `huguenot.documents`
  - `huguenot.pdf`
  - `huguenot.ui`
- Use plain dataclasses/value objects for matter concepts.
- Limit protocols to real seams such as repositories, renderers, converters, and bundlers.
- SQLite access must stay behind repository/service boundaries.

## Verification

Run the full local gate before claiming completion:

```bash
uv run ruff format --check
uv run ruff check
uv run pyright
uv run pytest
uv run bandit -r src
```

## Migrations

- Startup migrations must be non-interactive and idempotent.
- Migration files must be packaged with the app.
- If the selected migration tool cannot satisfy packaged startup behavior, reopen the dependency decision instead of papering over the failure.
