---
name: libercrawl-ui-review
description: Audit and refine Libercrawl's offline, premium dark-mode dashboard. Use for layout, typography, visual consistency, archive Inspect interaction, accessibility, and the personal-versus-public feature boundary.
---

# Libercrawl UI review workflow

1. Read `AGENTS.md`, `app/static/index.html`, `app/static/styles.css`, `app/static/app.js`, and `app/main.py` before making changes.
2. Preserve the CSS design tokens, minimal, high-contrast design restraint and system-font stack. Refine hierarchy, spacing, contrast, and responsiveness at widths 1440, 1024, 768, and 390 px; do not add proprietary fonts, frameworks, CDNs, or remote assets.
3. Run `node --check app/static/app.js` and `.venv/bin/python -m pytest -q` (create an isolated environment if needed). Add regression tests for any interaction changes.
4. Browser-smoke-test the FIRST Inspect button in Archive with at least one populated job and verify its inspector becomes visible, focuses, and scrolls into view; when API fails, verify `archiveNotice` appears. Avoid silently swallowing errors.
5. The public GitHub edition must have NO personal-only UI button or export API. Do not add them. Keep it general-purpose.
6. Never modify or delete the existing `engine/`, `.venv/`, `data/` and any `.env`, and never run Docker destructive commands. No accidental hosted extraction API calls. Never commit scraped data, auth tokens, Linux images, or backups.
7. Provide a concise change report, before/after screenshots if possible, test results, and any remaining limitations. Do not commit, push, or create GitHub remotes without explicit authorization.
