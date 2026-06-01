# procare-ingest

Self-hosted service that periodically syncs data from the (unofficial) Procare Online API into your own MySQL or Postgres database.

Built to run **anywhere on the deployment ladder**:

1. 🐍 **Local Python** — `python src/main.py`
2. 🐳 **Docker Compose** — `docker compose up`
3. ☸️ **k3s / Kubernetes via Helm** — `helm install`

> ⚠️ Procare does not publish a public API. This project uses the same endpoints the official web app calls. Use at your own risk; respect rate limits.

---

## What it syncs

| Entity | Source endpoint | Table |
|---|---|---|
| Rooms | `/api/web/rooms` | `rooms` |
| Kids | `/api/web/parent/kids/` | `kids` |
| Contacts | `/api/web/contacts` | `contacts`, `kid_contacts` |
| Daily activities | `/api/web/parent/daily_activities/` | `daily_activities` |
| Staff | `/api/web/staff` | `staff` |

Idempotent upserts; per-kid watermarks for daily activities.

---

## 1. Get a Procare auth token

The easiest path:

```bash
pip install httpx
python scripts/get_token.py
```

Enter your Procare email + password. The script prints your `auth_token`, your sites, and a ready-to-paste `.env` block.

**Or extract it from DevTools:**

1. Open <https://schools.procareconnect.com> and log in.
2. Open DevTools → **Network** tab → filter `XHR`.
3. Click any data request (e.g. `kids`).
4. In **Request Headers**, copy the value of `Authorization` (just the token — **no `Bearer ` prefix**).

---

## 2. Configure

Copy and edit:

```bash
cp .env.example .env
```

Minimum required:

```env
PROCARE_AUTH_TOKEN=...           # from step 1
PROCARE_SITE_URL=https://api-school.procareconnect.com
PROCARE_SITE_ID=<your-site-id>

DB_ADAPTER=mysql                 # or "postgres"
DB_HOST=localhost
DB_PORT=3306
DB_NAME=procare
DB_USER=procare
DB_PASSWORD=changeme
```

See `.env.example` for the full list (scheduling, log level, lookback window, etc.).

---

## 3. Run

### Option A — Local Python

```bash
pip install -r requirements.txt
python src/main.py
```

`RUN_ONCE=true` exits after one sync. Otherwise APScheduler runs on `SYNC_CRON` (default `*/15 * * * *`).

### Option B — Docker Compose

Brings up MySQL 8 + the sync service:

```bash
docker compose up -d
docker compose logs -f procare-sync
```

### Option C — Helm on k3s / Kubernetes

```bash
helm install procare-sync ./helm/procare-sync \
  --set secrets.procareAuthToken=$PROCARE_AUTH_TOKEN \
  --set config.procareSiteId=<site-id> \
  --set mysql.enabled=true \
  --set mysql.auth.rootPassword=changeme \
  --set mysql.auth.password=changeme
```

Two modes via `mode:`
- `cronjob` (default) — `RUN_ONCE=true`, `concurrencyPolicy: Forbid`.
- `deployment` — long-running pod with APScheduler.

Set `mysql.enabled=false` and point `config.dbHost` at an external DB to use your own.

---

## Repo structure

```
src/
  config.py            env-driven config
  auth.py              token cache + refresh
  client.py            httpx + retry + paginate
  db.py                engine/session factory
  models/              SQLAlchemy ORM models
  sync/
    base.py            upsert + watermark helpers
    {kids,rooms,contacts,staff,daily_activities}.py
    runner.py          orchestration order
  main.py              RUN_ONCE vs scheduler
scripts/
  get_token.py         interactive token helper
helm/procare-sync/     Helm chart (cronjob or deployment)
Dockerfile
docker-compose.yml
Makefile
```

---

## Make targets

```bash
make dev        # run locally
make build      # build docker image
make push       # push to registry (set IMAGE)
make compose-up
make compose-down
```

---

## License

MIT — see `LICENSE`.
