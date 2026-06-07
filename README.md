# procare-ingest

Self-hosted three-service stack that periodically syncs data from the
(unofficial) Procare Online API into a local SQLite database, and exposes
that data to dashboards and AI agents over REST + MCP — with built-in
failure notifications.

```
                    +--------------------+
                    ¦  Procare Online    ¦
                    ¦  (unofficial API)  ¦
                    +--------------------+
                             ¦ HTTPS
                +------------?-----------+
                ¦     procare-sync       ¦
                ¦   (k3s CronJob, Job)   ¦
                ¦ pull ? classify errors ¦
                +------------------------+
                             ¦ HTTP (bearer-auth)
              +--------------?--------------+
              ¦        procare-api          ¦
              ¦ - FastAPI (REST + ingest)   ¦
              ¦ - MCP server (/mcp)         ¦
              ¦ - SQLite on PVC (WAL)       ¦
              ¦ - Alerts + notifier         ¦
              ¦ - Heartbeat watchdog        ¦
              +-----------------------------+
                   ¦               ¦
        +----------?--+      +-----?---------+
        ¦ dashboards  ¦      ¦   AI agents   ¦
        ¦   (REST)    ¦      ¦ (MCP, Claude  ¦
        ¦             ¦      ¦  Desktop, …)  ¦
        +-------------+      +---------------+
```

> ?? Procare does not publish a public API. This project uses the same endpoints
> the official web app calls. Use at your own risk; respect rate limits.

---

## Why split this way

- **procare-sync** is a stateless `Job` — runs, exits. No DB driver, just `httpx`.
  Easy to fit anywhere in a k3s cluster.
- **procare-api** owns the SQLite file on a PVC. Single writer = no MySQL ops
  burden. Read concurrency via WAL.
- **Notifier + heartbeat** live inside procare-api so a stalled CronJob still
  gets caught (it's the api that notices the silent failure).

---

## What it syncs

| Entity | Source endpoint | Table |
|---|---|---|
| Rooms | `/api/web/parent/rooms/` | `rooms` |
| Kids | `/api/web/parent/kids/` | `kids` |
| Contacts | `/api/web/parent/contacts/` | `contacts` |
| Daily activities | `/api/web/parent/daily_activities/` | `daily_activities` |
| Staff | `/api/web/parent/staff/` | `staff` |

Plus `alerts` and `sync_state` tables maintained by the api.

---

## 1. Get a Procare auth token

Easiest:

```bash
pip install httpx
python scripts/get_token.py
```

Or extract from DevTools ? Network ? any XHR ? `Authorization` header
(value only, **no `Bearer `** prefix).

---

## 2. Run

### Option A — Docker Compose (recommended for local)

```bash
cp .env.example .env
# fill in PROCARE_AUTH_TOKEN (and PROCARE_SITE_ID) + set INGEST_TOKEN to any random string
docker compose up -d
docker compose logs -f procare-sync
```

REST: <http://localhost:8080/docs>  
MCP:  `http://localhost:8080/mcp`

### Option B — Local Python (two processes)

```bash
pip install -r requirements.txt -r requirements-sync.txt
# terminal 1
PYTHONPATH=src uvicorn api.main:app --port 8080
# terminal 2
PYTHONPATH=src python src/main.py
```

### Option C — k3s / Kubernetes via Helm

```bash
# 1. Install the api (long-running deployment + SQLite PVC)
helm install procare-api ./helm/procare-api \
  --set ingestToken=$INGEST_TOKEN \
  --set notify.backend=webhook \
  --set notify.webhookUrl=$NTFY_URL \
  --set notify.webhookFormat=ntfy

# 2. Install the sync CronJob, pointing at the api
helm install procare-sync ./helm/procare-sync \
  --set api.ingestToken=$INGEST_TOKEN \
  --set procare.authToken=$PROCARE_AUTH_TOKEN \
  --set procare.siteId=$PROCARE_SITE_ID
```

---

## 3. Use the data

### REST (dashboards)

```bash
curl http://procare-api/kids
curl 'http://procare-api/activities?date_from=2026-06-01&kid_id=...'
curl http://procare-api/alerts?acknowledged=false
```

Full schema: <http://procare-api/docs>

### MCP (agents)

Streamable HTTP at `/mcp`. Add to Claude Desktop:

```json
{
  "mcpServers": {
    "procare": {
      "url": "http://procare-api.local/mcp"
    }
  }
}
```

Tools available: `list_kids`, `get_kid`, `list_rooms`, `list_staff`,
`list_contacts`, `list_activities`, `counts`.

---

## 4. Notifications (so you actually know when it breaks)

Procare is unofficial ? tokens get rotated, accounts get locked, the API
might change shape. Three failure types are detected and notified:

| Source | When it fires |
|---|---|
| `auth_failed` (critical) | Procare returns 401/403 — token rotated or account locked |
| `rate_limited` (warning) | 429 from Procare |
| `http_error` / `network_error` (warning) | 5xx / connection issues |
| `sync_stalled` (warning) | api hasn't seen a successful sync within threshold (heartbeat) |
| `exception` (warning) | unhandled exception during sync |

Alerts are deduped per `(code, entity)` within `ALERT_COOLDOWN_MINUTES`
(default 60) so a 15-min CronJob won't ping you 96×/day for the same
problem.

### Pick a notifier backend (env on procare-api):

| Backend | env vars |
|---|---|
| Log only (default) | `NOTIFY_BACKEND=log` |
| Generic webhook | `NOTIFY_BACKEND=webhook`, `NOTIFY_WEBHOOK_URL=...`, `NOTIFY_WEBHOOK_FORMAT=generic` |
| Discord | `NOTIFY_WEBHOOK_FORMAT=discord` |
| Slack | `NOTIFY_WEBHOOK_FORMAT=slack` |
| ntfy.sh / Gotify | `NOTIFY_WEBHOOK_FORMAT=ntfy`, URL = your topic URL |
| SMTP | `NOTIFY_BACKEND=smtp` + `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TO`, `SMTP_FROM` |
| Apprise (80+ services) | `NOTIFY_BACKEND=apprise` + `APPRISE_URLS=...` (requires `pip install apprise`) |

You can list multiple: `NOTIFY_BACKEND=log,webhook,smtp`.

Manual alert browsing/ack:

```bash
curl http://procare-api/alerts?acknowledged=false
curl -X POST http://procare-api/alerts/42/ack
```

---

## Repo structure

```
src/
  api/                   procare-api service
    main.py              FastAPI app + MCP mount + heartbeat
    config.py            ApiConfig (env-driven)
    db.py                SQLite engine (WAL, FK on)
    routers/             REST endpoints (one per entity + ingest + alerts)
    mcp_server.py        MCP tools (list_kids, list_activities, ...)
    notifier.py          log / webhook / smtp / apprise
    heartbeat.py         background staleness watchdog
  sync/                  procare-sync service
    api_client.py        bearer-auth HTTP client for procare-api
    error_reporting.py   classify + report httpx errors as alerts
    runner.py            orchestrates entity syncs
    kids.py rooms.py contacts.py staff.py daily_activities.py
  shared/
    models.py            SQLAlchemy models (single source of truth)
  auth.py client.py      Procare HTTP client + token manager (used by sync)
  config.py main.py      sync config + entrypoint
helm/
  procare-api/           Deployment + Service + PVC + Ingress
  procare-sync/          CronJob only
Dockerfile.api
Dockerfile.sync
docker-compose.yml
requirements.txt         (api)
requirements-sync.txt    (sync)
```

---

## License

MIT — see `LICENSE`.