# Contributing to procare-sync

## How to Add a New Endpoint Syncer

### 1. Understand the Endpoint

First, capture the raw API response using DevTools or `scripts/get_token.py` plus a manual `curl`:

```bash
curl -H "Authorization: YOUR_TOKEN" \
  "https://YOUR_SITE.procareconnect.com/api/web/parent/NEW_ENDPOINT/"
```

### 2. Add a Model (if needed)

In `src/models/__init__.py`, add a new SQLAlchemy model following the existing pattern:

```python
class NewEntity(Base):
    __tablename__ = "new_entities"

    id = Column(String(64), primary_key=True)
    # ... your fields ...
    raw_json = Column(JSON)
    synced_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### 3. Create the Syncer Module

Create `src/sync/new_entity.py`:

```python
import logging
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from client import ProcareClient
from models import NewEntity
from sync.base import upsert_batch, set_watermark

logger = logging.getLogger(__name__)


def _map(raw: dict) -> dict:
    def get(*keys):
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return None

    return {
        "id": get("id", "uuid"),
        # map all fields with fallback aliases for API inconsistencies
        "raw_json": raw,
    }


def sync_new_entity(db: Session, client: ProcareClient) -> int:
    logger.info("Syncing new_entity...")
    try:
        total = 0
        for page in client.paginate("/api/web/parent/new_endpoint/"):
            mapped = [_map(r) for r in page if r.get("id")]
            if mapped:
                total += upsert_batch(db, NewEntity, mapped)
        set_watermark(db, "new_entity", datetime.utcnow(), total)
        logger.info("Synced %d new_entity records", total)
        return total
    except httpx.HTTPStatusError as e:
        if e.response.status_code in (403, 404):
            logger.warning("new_entity endpoint not available (%d), skipping", e.response.status_code)
            return 0
        raise
```

### 4. Add to Runner

In `src/sync/runner.py`, import and call your new syncer:

```python
from sync.new_entity import sync_new_entity

def run_full_sync(db, client, config):
    # ... existing syncs ...
    logger.info("--- Syncing new_entity ---")
    counts["new_entity"] = sync_new_entity(db, client)
    return counts
```

### 5. Test Manually

```bash
cp .env.example .env
# Fill in credentials
RUN_ONCE=true python src/main.py
```

Check the database for your new table and records.

## Code Style

- Follow existing patterns (field mapping with `get(*aliases)`, graceful 403/404 handling)
- Always store the full raw payload in `raw_json`
- Always call `set_watermark` at the end of a successful sync
- Log at INFO level for sync start/end with counts
- Log at WARNING for expected failures (403/404)
- Log at ERROR for unexpected failures

## Submitting Changes

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/add-new-endpoint`
3. Commit your changes with clear messages
4. Open a pull request with a description of the new endpoint and sample data (redact PII)
