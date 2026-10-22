# Architecture and Configuration

## Components

- **Browser frontend** — vanilla HTML/CSS/JavaScript in `app/static/`, using a local system-font stack and no required external design assets.
- **Dashboard API** — Python FastAPI server (`app/main.py`) for jobs, archive, status, exports, and UI content.
- **Local extraction client** — `app/engine.py` calls only an HTTP endpoint on localhost / loopback.
- **Target validation** — `app/security.py` validates public-domain URLs before the dashboard submits requests; it is not a complete SSRF defense.
- **SQLite archive** — `app/storage.py` creates `data/embercrawl.sqlite3`, using WAL mode and foreign keys, and stores job/page records.
- **Product candidates** — `app/product.py` parses HTML JSON-LD and common metadata without paid AI.
- **Upstream engine** — `engine/`, obtained from the source and exact revision identified in [third-party notices](../THIRD_PARTY_NOTICES.md) by `scripts/install.sh`, runs in Docker Compose.

## Upstream release pin and compatibility

| Item | Value |
| --- | --- |
| Engine source tag | `v2.11.0` |
| Exact checked-out commit | `ef12eb36b2f3382838dfe0a0c1a5add3d5df7fe5` |
| Compose file | `engine/docker-compose.yaml` |
| Docker project name | `embercrawl-engine` (compatibility with earlier installations) |
| Queue backend | `NUQ_BACKEND=pg` (PostgreSQL) |
| Dashboard API | `127.0.0.1:3210` |
| Local extraction API | `127.0.0.1:3002` |

The pinned Compose stack for this release includes API/workers, Playwright/Chromium, Redis, RabbitMQ, NuQ PostgreSQL, and FoundationDB-related services. FoundationDB is present in the pinned Compose stack even though Libercrawl selects PostgreSQL for its NuQ backend. Presence of an init container with a nonzero exit code does not by itself prove the API is unhealthy; verify the API independently.

`scripts/patch-engine.sh` adjusts the RabbitMQ health check to invoke `rabbitmq-diagnostics` as the `rabbitmq` user (through `gosu`) to avoid a cookie ownership race seen on some installations. The patch is limited to a precise line and may need review when changing engine versions.

## Configuration boundaries

**Libercrawl `.env`** contains dashboard preferences and its local engine URL:

```dotenv
LOCAL_ENGINE_URL=http://127.0.0.1:3002
APP_HOST=127.0.0.1
APP_PORT=3210
APP_DATA_DIR=./data
MAX_BATCH_URLS=30
MAX_CRAWL_PAGES=50
MAX_JOB_SECONDS=900
```

`MAX_BATCH_URLS`, `MAX_CRAWL_PAGES`, and `MAX_JOB_SECONDS` are clamped by the backend. The current `scripts/start.sh` and `scripts/start.ps1` pass the dashboard host and port explicitly to Uvicorn; modifying `APP_HOST`/`APP_PORT` alone does not override that command.

**Engine `engine/.env`** is separate. The installer creates an example local configuration with `NUQ_BACKEND=pg`, capped concurrency, a generated `BULL_AUTH_KEY`, `USE_DB_AUTHENTICATION=false`, and empty optional external provider settings. Keep it private. Changing backend implementations or upgrading the upstream release can require other configuration changes.

## Workflow

```text
Browser form --> POST /api/scrape | /api/batch | /api/crawl | /api/map
             --> SQLite job record (queued)
             --> In-process async worker (max two at once)
             --> Local extraction API /v2/* on localhost
             --> Process/store results in SQLite
             --> Archive / Inspect / export
```

- Job IDs are UUIDs; the app uses 202 Accepted for job creation.
- The dashboard's health probe is a **deliberately invalid** POST `{}` to `/v2/scrape`. A 400 or 422 response indicates that the expected route is alive, **not** that a real scrape succeeded.
- Engine-side crawl jobs are polled until completion/failure/cancellation. Job progress is reported in the dashboard.
- No background job resumption is implemented for dashboard restarts.

## Why keep the old SQLite filename and Compose project name?

For compatibility with earlier Libercrawl preview installations, the SQLite database file remains `embercrawl.sqlite3` and the engine Compose project retains `embercrawl-engine`. These are **internal technical identifiers**, not the public product name. Renaming them casually could hide existing data or spawn a second Docker stack.

## Port and deployment safety

Default: both the dashboard and engine are intended for **localhost only**. The extraction API has authentication disabled in the local setup. Do not expose the dashboard or the API through router port forwarding, a public reverse proxy, a shared LAN interface, or zero-trust remote access without designing and testing strong access controls, logging, TLS, and sandboxing first.

## Upstream compatibility

This guide documents the **pinned release**, not necessarily the latest upstream API. The third-party source, version, license, and our applied patch are disclosed in [third-party notices](../THIRD_PARTY_NOTICES.md). Review upstream's version-matched documentation and license notices before upgrading.
