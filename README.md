<div align="center">

# Libercrawl

### Extract the Web. Free the data.

**A local-first, open-source web extraction studio with a carefully designed dark interface.**

Scrape pages, collect URLs, crawl websites, review results, and export your data using a **separately downloaded, open-source extraction engine** running on your computer.

**Self-hosted** · **No hosted scraping subscription** · **Local SQLite archive** · **No required cloud AI**

</div>

---

## What is Libercrawl?

Libercrawl is a desktop-friendly **web application** that provides a polished interface for running a separately licensed, locally deployed extraction engine. It consists of a Python/FastAPI dashboard and a separate service launched through Docker Compose. You work in your browser; scraping and storage are handled by local services.

Libercrawl is designed for developers, researchers, data practitioners, and anyone who prefers to **own their extraction workflow**, rather than depend on a hosted scraping dashboard.

> **Independent software.** Libercrawl is an independently maintained interface to an external open-source engine. See [third-party notices](THIRD_PARTY_NOTICES.md) for source, license, modifications, and non-affiliation.

### Features

| Feature | What it does |
| --- | --- |
| **Single scrape** | Extracts one public HTTP/HTTPS webpage through the local extraction engine, including Markdown and HTML when returned by the engine. |
| **Batch scrape** | Processes a list of URLs in a single dashboard job (processed sequentially by Libercrawl, not a remote batch API). |
| **Website crawl** | Requests a bounded, depth-limited crawl with progress tracking and a Cancel action. |
| **URL map** | Discovers linked URLs without storing full page bodies; results export as JSON. |
| **Archive** | Stores job history and scraped pages in a local SQLite database. |
| **Inspect** | Opens job details, extracted-content previews, detected product information, and errors. |
| **Exports** | Downloads JSON, JSONL, Markdown, or CSV where appropriate. |
| **Product hints** | Attempts *deterministic* product-field extraction from page JSON-LD and HTML metadata; does not require an LLM. |
| **Dark UI** | Responsive charcoal interface, restrained accents, and local system fonts without remote design assets. |

Product fields are **best-effort candidates**, not verified records. Missing sizes, variants, prices, or materials remain missing; data quality depends on the source website. AI-based extraction is **not included in this dashboard**.

### What makes it different?

- **No hosted scraping API key or credits** are required for Libercrawl's default workflows.
- The **dashboard only accepts a local extraction-engine endpoint** (`localhost`, `127.0.0.1`, or `::1`).
- Scraped job history lives in **SQLite on your computer**, not a hosted database.
- A pinned third-party engine source checkout helps make installations reproducible.
- You can inspect, modify, and self-host the app's code under its open-source license.

**Important distinction:** Self-hosted does *not* mean offline. Initial installation downloads source, packages, and container images. Scraping itself sends requests to target websites. Internet, electricity, computer resources, and any optional services still have costs.

## System requirements

These are **practical estimates for the multi-container stack, not official benchmarks or hard guarantees**. The first build can be substantial, especially on Windows with WSL2.

| Requirement | Minimum to try | Recommended |
| --- | --- | --- |
| **OS** | 64-bit Linux with Docker; or Windows 10/11 with WSL2 Ubuntu | Current Ubuntu LTS on Linux or WSL2 |
| **CPU** | 2 modern x86-64 cores (may be slow) | 4+ cores |
| **RAM** | 8 GB physical RAM (tight; may fail under load) | 16 GB+, especially for browser-based crawling |
| **Free disk space** | 30 GB before first build | 50 GB+ for images, builds, logs, and collected data |
| **GPU** | Not required | Not required |
| **Network** | Internet for installation and target sites | Stable broadband |
| **Software** | Git, Docker Engine, Docker Compose v2, Python 3 with `venv` | Up-to-date packages, Docker service managed by systemd |

The full installed system can occupy tens of gigabytes; actual footprint varies by OS, browser images, caches, and archive size. Check usage with `docker system df`, `du -sh ~/libercrawl`, and `df -h ~`.

**Windows security:** Windows 10 reached end of standard support on October 14, 2025. For an internet-connected scraping machine, use Windows 11 or a supported Windows 10 Extended Security Updates (ESU) arrangement. See [Microsoft’s notice](https://learn.microsoft.com/en-us/lifecycle/announcements/windows-10-end-of-support).

**Software compatibility:** The Linux/WSL2 path is the field-tested setup. Windows PowerShell scripts are included, but **native Windows/Docker Desktop operation has not been equivalently validated**. Docker Desktop is not required for the recommended path.

## Quick start — Linux / WSL2 Ubuntu

> Complete Windows-specific setup is in **[docs/INSTALL.md](docs/INSTALL.md)**. Read it if Docker or WSL2 is not installed.

```bash
# 1. Install prerequisites in Ubuntu (package names can vary by release)
sudo apt update
sudo apt install -y git docker.io docker-compose-v2 python3 python3-venv python3-pip
sudo systemctl enable --now docker

# 2. Clone the repository (replace the placeholder with YOUR repository URL)
git clone https://github.com/YOUR_USERNAME/libercrawl.git
cd libercrawl

# 3. Install the local application and the pinned extraction engine source
bash scripts/install.sh

# 4. Build/start the engine and run the dashboard
bash scripts/start.sh
```

In your browser, open **http://127.0.0.1:3210**.

The local extraction API is published on **http://127.0.0.1:3002**. Neither endpoint should be exposed directly to the public internet.

If your Ubuntu account cannot talk to Docker, see the [Docker permissions section](docs/INSTALL.md#docker-permissions). If your Python virtual environment fails with `ensurepip is not available`, see [Troubleshooting](docs/TROUBLESHOOTING.md#python-venv-or-ensurepip-is-missing).

### Verify the installation

```bash
# In another terminal, while Libercrawl is running:
docker ps
curl -s http://127.0.0.1:3210/api/status

# Basic route reachability (HTTP 400 or 422 is expected: no URL supplied)
curl -i -X POST http://127.0.0.1:3002/v2/scrape \
  -H 'Content-Type: application/json' -d '{}'
```

An **Online** status only means the local extraction API is responding. To verify end-to-end scraping, submit `https://example.org` using **Single scrape** and check that the completed job contains Markdown in **Archive → Inspect**.

### Start and stop

```bash
bash scripts/start.sh       # Start engine containers + dashboard (foreground)
# Ctrl+C                    # Stop dashboard only
bash scripts/stop.sh        # Stop engine containers; retains local SQLite archive
```

`start.sh` may rebuild source-based containers on future runs; previously completed layers are cached where possible. Run `scripts/stop.sh` from a separate terminal after stopping the dashboard.

## How to use it

1. Open **http://127.0.0.1:3210** and check the **Engine online** indicator.
2. Choose **Single scrape**, **Batch scrape**, **Crawl site**, or **Map URLs**.
3. Enter public website URLs and choose available limits.
4. Submit the job, then open **Archive**.
5. Click **Inspect** to review the results, detected product fields, and errors; download an export if desired.

For output formats, job limits, data retention, and current feature limitations, see **[docs/USER_GUIDE.md](docs/USER_GUIDE.md)**.

## Architecture at a glance

```text
Your browser (127.0.0.1:3210)
        |
        v
Libercrawl Dashboard  [FastAPI + local static HTML/CSS/JS]
        |                 \
        |                  +--> SQLite archive  [data/embercrawl.sqlite3]
        v
Local extraction API (127.0.0.1:3002)
        |
        +--> Playwright/Chromium
        +--> Redis / RabbitMQ
        +--> PostgreSQL (NuQ queue)
        +--> FoundationDB services present in pinned Compose stack
        |
        v
Public target websites (outbound internet requests)
```

The installer clones the **exact source revision** documented in [third-party notices](THIRD_PARTY_NOTICES.md) into the Git-ignored `engine/` directory. It applies a small RabbitMQ health-check compatibility patch and configures `NUQ_BACKEND=pg`. This release pin is intentional: the upstream project's newest installation instructions may describe a newer version and **should not be mixed blindly with this release's Compose file**.

Details: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Configuration

Libercrawl's `.env` is created from [`.env.example`](.env.example) during installation. Important settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LOCAL_ENGINE_URL` | `http://127.0.0.1:3002` | Local-only engine endpoint |
| `APP_HOST` | `127.0.0.1` | Dashboard bind-address setting (see note) |
| `APP_PORT` | `3210` | Dashboard port setting (see note) |
| `APP_DATA_DIR` | `./data` | Local SQLite data directory |
| `MAX_BATCH_URLS` | `30` | Maximum URLs per batch, capped at 100 in code |
| `MAX_CRAWL_PAGES` | `50` | Maximum crawl pages per job, capped at 250 in code |
| `MAX_JOB_SECONDS` | `900` | Per-job timeout in seconds; capped to 60–3600 |

**Note:** The shipped `start.sh` explicitly binds Uvicorn to `127.0.0.1:3210`; changing `APP_HOST`/`APP_PORT` alone does **not** change that startup command. Use a reviewed startup-script change if a different local port is needed. Keep the service local.

The separately downloaded engine's `engine/.env` contains engine-specific settings such as `NUQ_BACKEND=pg`. **Never commit either `.env` file.** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#configuration-boundaries).

## Security and privacy

Libercrawl is designed for **trusted local use**, not for exposing to strangers. The default extraction-engine API has authentication disabled; its network exposure must remain restricted to loopback. The dashboard also has no account/login system. Target URL checks block common local/private-address targets, but they are not a substitute for network isolation or a comprehensive defense against SSRF and redirects.

The Libercrawl frontend does not require telemetry, CDN assets, or remote fonts. The dashboard archives results in local SQLite; outbound requests reach target websites and may be logged by those websites and network intermediaries. See [docs/SECURITY_AND_BACKUPS.md](docs/SECURITY_AND_BACKUPS.md) for safe deployment, backup, and retention guidance.

## Limitations

- Not all features of a hosted extraction service are included in the open-source engine or surfaced by this UI.
- No built-in hosted AI, model account, or guaranteed structured-product extraction.
- Crawls are bounded, and the current dashboard does **not** follow completed-crawl pagination links; very large crawls may require further work.
- Dashboard job execution is in-process. Running/queued jobs are marked interrupted after a dashboard restart; this is not a durable distributed task queue.
- The default engine Compose setup is a **local development baseline, not a hardened production deployment**. Some queue service data may not persist across destructive service replacement.
- The UI permits public domain URLs, not arbitrary internal network targets.

## Documentation

- **[Installation & requirements](docs/INSTALL.md)** — Linux and Windows/WSL2 setup; first run.
- **[User guide](docs/USER_GUIDE.md)** — workflows, archive, exports, limits.
- **[Architecture & configuration](docs/ARCHITECTURE.md)** — internals and upstream version pin.
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — WSL DNS, permissions, Python, RabbitMQ, API offline, browser builds.
- **[Security & backups](docs/SECURITY_AND_BACKUPS.md)** — trust boundaries, backups, data hygiene.
- **[Publishing checklist](docs/GITHUB_PUBLISHING.md)** — safe first commit, license, secrets, and release notes.
- **[Codex task](docs/CODEX_TASK.md)** — optional UI review with the bundled repository skill.

## Development and tests

```bash
# After install.sh (which creates .venv):
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
node --check app/static/app.js  # optional: requires Node.js installed on host
```

The existing release has a 23-test offline Python suite. Offline tests use mocks and **do not establish that a complete local extraction-engine deployment works on every machine**. A real scraping smoke test remains necessary after installation.

## License, attribution and publication checks

Libercrawl source is offered under **GNU AGPL-3.0-or-later**. See [LICENSE](LICENSE) and [LICENSE_SCOPE.md](LICENSE_SCOPE.md). The separately downloaded engine and dependencies retain their own copyright and license obligations. **Required attribution, upstream source details and modifications** are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

**Before publishing under this name:** [review the existing name collision and outstanding release risks](docs/PRE_PUBLICATION_RISK_REVIEW.md).

---

<div align="center"><strong>Extract the Web. Free the data.</strong></div>
