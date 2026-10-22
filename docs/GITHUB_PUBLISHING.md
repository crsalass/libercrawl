# GitHub publishing checklist — Libercrawl v1.1.3

**Name changed to Libercrawl.** Another open-source crawler uses the similar name `LibreCrawl` at https://librecrawl.com/. This avoids the exact same spelling but is **not a trademark clearance**. See `PRE_PUBLICATION_RISK_REVIEW.md` before publishing.

## Suggested GitHub About description (after name clearance)

> An open-source, local-first web extraction workspace. Scrape, crawl, map and archive websites through a clean dark interface with a self-hosted engine and no required hosted scraping subscription.

Suggested topics: `self-hosted`, `web-scraping`, `open-source`, `docker`, `fastapi`, `sqlite`, `web-crawler`, `data-extraction`, `local-first`.

## Before the first public commit

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

## Commit procedure (only after review)

```bash
git init -b main
git add .
git status --short
git diff --cached --stat
# Inspect any unexpected path or secrets before committing.
git commit -m "docs: prepare local-first web extraction release"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

## Draft release notes

**Extract the Web. Free the data.**

A self-hosted local web extraction dashboard with individual and sequential multi-URL scraping, bounded crawling, URL discovery, SQLite archives, best-effort deterministic product metadata extraction, and exports in JSON/JSONL/Markdown/CSV. Responsive dark interface with local system fonts and no mandatory remote frontend assets.

The application requires a separately licensed open-source engine, installed from a pinned source revision. No hosted scraping account or cloud AI service is required for normal use. Installation and scraping still require network access. See third-party notices for source provenance and licensing.

**Limits:** The dashboard is not a multi-user service, does not support authentication, and must not be exposed publicly. Crawl result pagination and durable job resumption are not implemented. Product fields require verification.
