# procare-sync

A self-hosted service that syncs data from [Procare Online](https://procareconnect.com/)'s unofficial web API into a local MySQL or PostgreSQL database. Query your own childcare data for reporting, dashboards, and integrations.

> **⚠️ Disclaimer:** This project uses Procare Online's internal/unofficial API endpoints, reverse-engineered from browser traffic. These are undocumented, subject to change without notice, and not affiliated with or endorsed by Procare Software. Use at your own risk and in compliance with Procare's terms of service.

---

## What It Syncs

| Entity | Description |
|---|---|
| `kids` | Enrolled children |
| `rooms` | Classrooms |
| `contacts` | Parents / guardians |
| `kid_contacts` | Kid ↔ contact relationships |
| `daily_activities` | Attendance, meals, naps, notes, photos |
| `staff` | Staff members |
| `sites` | Site/center info from login |
| `sync_state` | Watermarks for incremental sync |

All tables are created automatically on first run. Every row stores the full raw API payload in a `raw_json` column for forward-compatibility.

---

## Prerequisites

| Path | Requirements |
|---|---|
| Local Python | Python 3.12+, MySQL or Postgres running locally |
| Docker Compose | Docker Desktop (or Docker + Compose plugin) |
| Helm / k3s | kubectl + Helm 3, a running k3s cluster |

---

## Step 1 — Get Your Auth Token

You need a Procare auth token before running anything. Two options:

### Option A — Helper script (easiest)

```bash
pip install httpx
python scripts/get_token.py
```

The script prompts for your Procare email and password, authenticates, and prints your token plus the `.env` values to copy.

### Option B — Browser DevTools

1. Open [app.procareconnect.com](https://app.procareconnect.com) in Chrome or Firefox
2. Open **DevTools → Network tab**
3. Log in to your Procare account
4. Find the `sessions` network request
5. In the **Response** tab, copy:
   - `auth_token` → `PROCARE_AUTH_TOKEN`
   - `sites[0].base_url` → `PROCARE_SITE_URL`
   - `sites[0].id` → `PROCARE_SITE_ID`

---

## Step 2 — Configure

```bash
cp .env.example .env
```

Open `.env` and fill in at minimum:

```ini
PROCARE_AUTH_TOKEN=online_auth_xxxxxxxxxxxx   # from Step 1
PROCARE_SITE_URL=https://api-school.procareconnect.com  # from Step 1
DB_PASSWORD=yourpassword
```

See the [Environment Variables](#environment-variables) section for all options.

---

## Step 3 — Run

Choose the path that fits your setup:

### 🐍 Local Python

Best for development or one-off syncs.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Make sure MySQL/Postgres is running and DB_HOST, DB_PASSWORD are set in .env

# Run once and exit
RUN_ONCE=true python src/main.py

# Or run continuously on a schedule
python src/main.py
```

### 🐳 Docker Compose

Best for local home lab use. Starts MySQL automatically.

```bash
docker compose up --build
```

MySQL is included — no separate database needed. The sync container waits for MySQL to be healthy before starting. Data persists in Docker named volumes.

To run a one-off sync without the background scheduler:

```bash
docker compose run --rm procare-sync python src/main.py
# (with RUN_ONCE=true in your .env)
```

### ☸️ Helm / k3s

Best for persistent home lab deployment. Two modes available:

**CronJob mode** (default — runs on a schedule, one pod per sync):

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm dependency update ./helm/procare-sync

helm install procare-sync ./helm/procare-sync \
  --set procare.authToken=YOUR_TOKEN \
  --set procare.siteUrl=https://YOUR_SITE.procareconnect.com \
  --set db.password=changeme \
  --set mysql.auth.password=changeme \
  --set mysql.auth.rootPassword=rootchangeme
```

**Deployment mode** (long-running pod with internal scheduler):

```bash
helm install procare-sync ./helm/procare-sync \
  --set mode=deployment \
  --set procare.authToken=YOUR_TOKEN \
  --set db.password=changeme \
  --set mysql.auth.password=changeme
```

**External database** (skip bundled MySQL):

```bash
helm install procare-sync ./helm/procare-sync \
  --set mysql.enabled=false \
  --set db.host=my-mysql-host \
  --set db.password=changeme \
  --set procare.authToken=YOUR_TOKEN
```

Verify it's running:

```bash
kubectl get cronjobs          # cronjob mode
kubectl get deployments       # deployment mode
kubectl logs -l app.kubernetes.io/name=procare-sync
```

---

## Repository Structure

```
procare-ingest/
├── src/
│   ├── config.py              # All settings from env vars
│   ├── auth.py                # Token manager (env → cache → login)
│   ├── client.py              # Authenticated HTTP client + pagination
│   ├── db.py                  # SQLAlchemy engine + session factory
│   ├── main.py                # Entrypoint: RUN_ONCE or scheduler
│   ├── models/
│   │   └── __init__.py        # All ORM models
│   └── sync/
│       ├── base.py            # upsert helpers + watermarks
│       ├── runner.py          # Orchestrates all syncs in order
│       ├── kids.py
│       ├── rooms.py
│       ├── contacts.py
│       ├── staff.py
│       └── daily_activities.py
├── helm/procare-sync/         # Helm chart (CronJob + Deployment)
├── scripts/
│   └── get_token.py           # Interactive token extractor
├── Dockerfile
├── docker-compose.yml
├── Makefile                   # make dev / build / push / compose-up
├── requirements.txt
└── .env.example
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. All settings come from environment variables — nothing is hardcoded.

| Variable | Default | Required | Description |
|---|---|---|---|
| `PROCARE_AUTH_TOKEN` | — | One of A or B | Pre-obtained token (preferred) |
| `PROCARE_EMAIL` | — | One of A or B | Procare login email |
| `PROCARE_PASSWORD` | — | One of A or B | Procare login password |
| `PROCARE_SITE_URL` | `https://api-school.procareconnect.com` | Yes | From login response |
| `PROCARE_SITE_ID` | — | Recommended | Site UUID from login response |
| `PROCARE_AUTH_URL` | `https://online-auth.procareconnect.com/sessions/` | No | Override for testing |
| `DB_ADAPTER` | `mysql` | No | `mysql` or `postgres` |
| `DB_HOST` | `localhost` | Yes | Database host |
| `DB_PORT` | `3306` | No | Database port |
| `DB_NAME` | `procare` | No | Database name |
| `DB_USER` | `procare` | No | Database username |
| `DB_PASSWORD` | — | Yes | Database password |
| `SYNC_INTERVAL_MINUTES` | `15` | No | How often to sync (scheduler mode) |
| `ACTIVITY_LOOKBACK_DAYS` | `30` | No | Days back on first activity sync |
| `RUN_ONCE` | `false` | No | Exit after one sync (for CronJob / scripts) |
| `PAGE_SIZE` | `100` | No | API records per page |
| `TOKEN_CACHE_PATH` | `/data/.token_cache.json` | No | Where to persist auth token |

---

## Makefile Targets

```bash
make dev          # Run a one-off sync locally (RUN_ONCE=true)
make build        # Build Docker image
make push         # Push Docker image to registry
make compose-up   # docker compose up --build
make compose-down # docker compose down
make lint         # Python syntax check all src files
```

---

## Releasing a New Image

Push a semver tag to trigger a multi-arch (amd64 + arm64) build and push to `ghcr.io`:

```bash
git tag v0.1.0
git push --tags
```

The GitHub Actions workflow publishes `ghcr.io/dafrimer/procare-ingest:0.1.0` automatically.

---

## Non-Goals (v1)

- No write operations — read-only sync only
- No real-time / webhook support
- No REST API layer on top of the database
- No UI or dashboard
- No multi-account / multi-site support
- No admin/staff role support (carer role only)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add support for new Procare endpoints.
