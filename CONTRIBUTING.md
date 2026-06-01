# Contributing

## Dev setup

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env        # fill in your values
python src/main.py
```

## Adding a new endpoint syncer

The sync framework is a tiny pattern — one file per entity.

1. **Add the ORM model** in `src/models/__init__.py`. Pick a sensible primary key (Procare IDs are stable).

2. **Create `src/sync/<entity>.py`** with two functions:

   ```python
   def _map(record: dict) -> dict:
       """Procare API record → ORM column dict."""
       return {"id": record["id"], ...}

   def sync_<entity>(client, session, config) -> int:
       count = 0
       for batch in client.paginate(f"/api/web/{endpoint}"):
           rows = [_map(r) for r in batch]
           upsert_batch(session, MyModel, rows, ["id"])
           count += len(rows)
       return count
   ```

   Use `upsert_batch` from `src/sync/base.py`. Use `get_watermark` / `set_watermark` if the endpoint supports an incremental cursor.

3. **Register in `src/sync/runner.py`** in the correct order (parents before children — e.g. rooms before kids).

4. **Handle missing access gracefully.** Some endpoints return 403/404 depending on account type. Wrap the call so it logs a warning and returns 0 rather than crashing the whole run.

## Code style

- Type hints everywhere new code is added.
- `logging` module — never `print` in `src/`.
- Keep functions small; one responsibility each.

## Commits

Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`).
Each PR should be a single logical change — see merged PR history for examples.

## Pull requests

- Branch from `main`.
- One feature per PR.
- Squash-merge.
- Include a brief description of what changed and why.
