# GitHub publication review — Libercrawl public edition

Repository: [crsalass/libercrawl](https://github.com/crsalass/libercrawl). Publication is a separate, explicitly approved step; a local documentation review does not authorize commits, pushes, merges, or releases.

**Name changed to Libercrawl.** Another open-source crawler uses the similar name `LibreCrawl` at https://librecrawl.com/. This spelling difference does **not establish name clearance**. See [the existing risk review](PRE_PUBLICATION_RISK_REVIEW.md) before publishing.

## Suggested GitHub About description (after name clearance)

> An open-source, local-first web extraction workspace. Scrape, crawl, map and archive websites through a clean dark interface with a self-hosted engine and no required hosted scraping subscription.

Suggested topics: `self-hosted`, `web-scraping`, `open-source`, `docker`, `fastapi`, `sqlite`, `web-crawler`, `data-extraction`, `local-first`.

## Before a source release

- [ ] Review the remaining Libercrawl / LibreCrawl name similarity and check relevant trademark registers; seek professional advice where necessary.
- [ ] Publish this **GitHub Edition**, not any personal/private build.
- [ ] Retain the unmodified full GNU AGPL license in `LICENSE`.
- [ ] Retain `THIRD_PARTY_NOTICES.md`, `LICENSE_SCOPE.md`, and the source/patch attribution for the separately downloaded engine.
- [ ] Confirm source code and install scripts identify and fetch the pinned upstream release truthfully. Do not suggest that you authored the upstream engine.
- [ ] Confirm `engine/`, `.venv/`, local databases, `.env` files, Docker images, browser profiles and secrets are excluded.
- [ ] Confirm local-only defaults; do not publish an unauthenticated server publicly.
- [ ] Test offline suite, JS syntax and a real local end-to-end scrape.
- [ ] Check all dependencies and container image license notices before distributing binaries.
- [ ] Manually review `git status` / `git diff --cached` and search for secrets, personal data and private identifiers.
- [ ] Read `docs/PRE_PUBLICATION_RISK_REVIEW.md` for unresolved claims/security/legal considerations.

## Local review commands

For an existing checkout, review the branch and changes without reinitializing Git or changing remotes:

```bash
git status --short --branch
git diff --stat
git diff --check
git diff
```

Run `python -m pytest -q` with the development dependencies installed and a disposable `APP_DATA_DIR`, then `node --check app/static/app.js`. Refresh the SHA-256 entries for changed public files and new assets, excluding the manifest itself. Use `sha256sum -c SHA256SUMS.txt` on Linux/WSL2 with checkout bytes free of line-ending conversion. Checksums detect changed bytes; this manifest is not a signed authenticity guarantee.

Use only screenshots of the public edition, with a clear account of empty, offline, or fixture states. Preserve [screenshot provenance](assets/README.md), and never include a personal installation, secrets, scraped customer data, or fabricated successful jobs.

Commit, push, merge, and release commands require separate approval after review. No such commands are part of this checklist's local verification.

## Draft release notes

**Extract the Web. Free the data.**

A self-hosted local web extraction dashboard with individual and sequential multi-URL scraping, bounded crawling, URL discovery, SQLite archives, best-effort deterministic product metadata extraction, and exports in JSON/JSONL/Markdown/CSV. Responsive dark interface with local system fonts and no mandatory remote frontend assets.

The application requires a separately licensed open-source engine, installed from a pinned source revision. No hosted scraping account or cloud AI service is required for normal use. Installation and scraping still require network access. See third-party notices for source provenance and licensing.

**Limits:** The dashboard is not a multi-user service, does not support authentication, and must not be exposed publicly. Crawl result pagination and durable job resumption are not implemented. Product fields require verification.
