# Security, Privacy and Backups

## Threat model

Libercrawl is intended for **one trusted person on a local computer**. It is not an internet-facing, multi-user, hosted scraping platform. The default extraction engine has `USE_DB_AUTHENTICATION=false` and the dashboard has no authentication. **Do not expose either service publicly** without adding an appropriate security architecture.

### Data flows

- Your browser talks to the local dashboard (`127.0.0.1:3210`).
- The dashboard talks to your local extraction API (`127.0.0.1:3002`).
- The engine makes outbound HTTP/HTTPS requests to the public websites you ask it to scrape.
- Dashboard job/page records are saved to local SQLite.
- Initial installation downloads software from GitHub, Ubuntu/Python/container registries, and other dependency mirrors.

There is **no required hosted scraping API dependency** and no external CDN or font requirement for Libercrawl's static UI. This does **not** promise complete isolation from all third-party internet traffic or rule out optional upstream provider integrations if you configure them yourself.

### Target URL validation

Libercrawl validates URL syntax and checks public DNS resolution before dispatching jobs. It blocks localhost, direct IP-address targets, many internal/special-use suffixes, nonstandard ports, and embedded credentials. **These controls are not exhaustive**: DNS rebinding, redirects, and network configurations can require additional protection in the engine or firewall. Treat the entire application as unsafe to expose to arbitrary users.

### Data retention and protection

The dashboard's SQLite archive contains URLs and scraped content, possibly including material that the target website reveals. Anyone with local access to the application or filesystem may be able to inspect those records. Use OS-level disk encryption, correct filesystem permissions, and a separate machine/user for untrusted web scraping where appropriate.

Do not scrape private personal information or content you are not authorized to access. Respect website terms, applicable laws, copyright, robots policies where appropriate, and rate limits.

## Back up your Libercrawl archive

Archive file: `data/embercrawl.sqlite3`. Because SQLite uses **WAL journaling**, do not assume that copying only the open database file captures all recent writes. Use SQLite's online backup API (included with Python):

```bash
cd ~/libercrawl
mkdir -p "$HOME/libercrawl-backups"
.venv/bin/python - <<'PY'
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
src = Path('data/embercrawl.sqlite3')
if not src.exists():
    raise SystemExit('No local archive found yet.')
folder = Path.home() / 'libercrawl-backups'
folder.mkdir(parents=True, exist_ok=True)
dest = folder / f'libercrawl-{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-UTC.sqlite3'
with sqlite3.connect(src) as original, sqlite3.connect(dest) as backup:
    original.backup(backup)
print('SQLite backup:', dest)
PY
```

Copy the resulting file to another drive or encrypted backup location. To restore, stop the dashboard, keep a copy of the existing `data/` directory, and restore the backed-up SQLite file to the original name. Verify the archive opens before deleting any earlier copy.

## What GitHub does and does not back up

**Commit to GitHub:** public source, README, `docs/`, `.env.example`, scripts, tests, coding agent instructions, and configuration patch scripts.

**Never commit:** live `.env`/`engine/.env`, credentials, SQLite archives, Docker volumes/images, browser caches, `.venv/`, scraped customer data, or WSL filesystem backups. `.gitignore` prevents common mistakes but **always review `git status` and staged changes** before pushing.

A GitHub source repository lets you rebuild the application, but it does **not** restore your OS, Docker volumes, runtime secrets, or extracted results.

### Full-system recovery

For WSL2 users, a complete Linux environment backup is possible with `wsl --export`, after stopping Docker and shutting down the distribution. These archives can be **tens of gigabytes**. Keep them on a separate drive if exact system-state recovery is important. Unregistering a WSL distribution (`wsl --unregister`) permanently deletes that distribution's filesystem. Never unregister the only working copy.

## Docker data warning

The pinned upstream Docker Compose configuration is a developer-oriented deployment; not every backend data service is guaranteed to survive destructive Compose operations. `docker compose down` is different from `docker compose down -v`. Avoid `-v` unless you explicitly intend to delete volumes. For a production deployment, review upstream persistence, TLS, authentication, network access, monitoring, resource limits, and disaster-recovery requirements.

## Licensing and redistribution

Libercrawl source is offered under **AGPL-3.0-or-later**, with the full license text in `LICENSE`. The upstream extraction engine and third-party dependencies have separate license obligations. The full AGPL text is included at the repository root, and the [third-party notices](../THIRD_PARTY_NOTICES.md) preserve source attribution and document our compatibility patch. This public source ZIP excludes the downloaded upstream checkout. Packaging and distributing compiled images needs a separate license/SBOM review.
