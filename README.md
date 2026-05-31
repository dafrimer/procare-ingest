# procare-sync

A self-hosted service that syncs data from [Procare Online](https://procareconnect.com/)'s unofficial API into a MySQL or PostgreSQL database for reporting, analytics, and integration.

> **Disclaimer:** This project uses Procare Online's internal/unofficial API endpoints. These are subject to change without notice. This is not affiliated with or endorsed by Procare Software. Use at your own risk. Comply with Procare's terms of service.

---

## What This Does

- Authenticates with Procare Online (token or email/password)
- Periodically fetches kids, rooms, contacts, staff, and daily activities
- Upserts all records into MySQL or PostgreSQL
- Runs as a Docker container, CronJob, or Kubernetes Deployment

---

## Quick Start: Getting Your Token

The easiest approach is to extract a token using your browser's DevTools:

1. Open [Procare Online](https://app.procareconnect.com) in Chrome/Firefox
2. Open DevTools → Network tab
3. Log in to your Procare account
4. In the Network tab, find the `sessions` request
5. Look at the response JSON for `auth_token`
6. Also note `sites[0].id` (your `PROCARE_SITE_ID`) and `sites[0].base_url` (your `PROCARE_SITE_URL`)

Alternatively, use the helper script:

```bash
pip install httpx
python scripts/get_token.py
```

---

## Local Python Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_ORG/procare-sync.git
cd procare-sync

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values

# Run once
RUN_ONCE=true python src/main.py
```

---

## Docker Compose Quickstart

```bash
cp .env.example .env
# Edit .env — set PROCARE_AUTH_TOKEN, DB_PASSWORD at minimum

docker compose up --build
```

MySQL starts automatically. The sync service runs on the configured interval.

---

## Helm / k3s Quickstart

```bash
# Add bitnami repo (for bundled MySQL)
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install with bundled MySQL
helm install procare-sync ./helm/procare-sync \
  --set procare.authToken=YOUR_TOKEN \
  --set procare.siteUrl=https://YOUR_SITE.procareconnect.com \
  --set db.password=changeme \
  --set mysql.auth.password=changeme \
  --set mysql.auth.rootPassword=rootchangeme

# Install against external DB (no bundled MySQL)
helm install procare-sync ./helm/procare-sync \
  --set mysql.enabled=false \
  --set db.host=my-mysql-host \
  --set db.password=changeme \
  --set procare.authToken=YOUR_TOKEN

# Use deployment mode instead of cronjob
helm install procare-sync ./helm/procare-sync \
  --set mode=deployment \
  --set sync.intervalMinutes=15 \
  --set procare.authToken=YOUR_TOKEN \
  --set db.password=changeme \
  --set mysql.auth.password=changeme
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PROCARE_AUTH_TOKEN` | — | Pre-obtained auth token (preferred) |
| `PROCARE_EMAIL` | — | Login email (alternative to token) |
| `PROCARE_PASSWORD` | — | Login password (alternative to token) |
| `PROCARE_SITE_URL` | `https://api-school.procareconnect.com` | API base URL |
| `PROCARE_SITE_ID` | — | Site UUID |
| `PROCARE_AUTH_URL` | `https://online-auth.procareconnect.com/sessions/` | Auth endpoint |
| `DB_ADAPTER` | `mysql` | `mysql` or `postgres` |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `3306` | Database port |
| `DB_NAME` | `procare` | Database name |
| `DB_USER` | `procare` | Database user |
| `DB_PASSWORD` | — | Database password (required) |
| `SYNC_INTERVAL_MINUTES` | `15` | Sync interval (deployment mode) |
| `ACTIVITY_LOOKBACK_DAYS` | `30` | Days back for first activity sync |
| `RUN_ONCE` | `false` | Exit after one sync |
| `PAGE_SIZE` | `100` | Records per API page |
| `TOKEN_CACHE_PATH` | `/data/.token_cache.json` | Token cache file |

---

## Non-Goals

- **Not a real-time system** — designed for periodic batch sync only
- **No write-back** — this service is read-only from Procare's perspective
- **No UI** — query the database directly or connect your own BI tool
- **No official API support** — uses unofficial endpoints that may break

---

## Database Schema

Tables created automatically on first run:

- `sites` — Procare site info
- `rooms` — Classroom/room records
- `kids` — Child enrollment records
- `contacts` — Parent/guardian contacts
- `kid_contacts` — Kid ↔ contact relationships
- `daily_activities` — Daily activity log (attendance, meals, naps, etc.)
- `staff` — Staff members
- `sync_state` — Sync watermarks per entity
