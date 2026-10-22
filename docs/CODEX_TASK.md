# Task for Codex — Libercrawl design polish and stability audit

Use the **`$libercrawl-ui-review`** repository skill first. Discover any additionally available frontend testing/accessibility/design skills and apply them only if appropriate; do not install untrusted tools or use paid APIs.

Current release already includes a minimal dark theme, system font stack, renamed Libercrawl branding, a two-line hero (`Extract the Web. Free the data.`), safer Archive Inspect flow, and a public-edition removal of the personal export. Audit and refine without rewriting the stack.

## Acceptance criteria

1. Visual: consistent typography scale, spacing, button sizes and focus states. Palette based on charcoal, ink and restrained blue (`#76a9ff`), readable contrast, responsive at 390/768/1024/1440 px, reduced-motion support.
2. Exact brand text: **Libercrawl**; exact hero text: **Extract the Web. Free the data.** (line breaks may be present).
3. Archive: first `Inspect` button must open the correct saved job and show its inspector, even on the Archive tab. An API error must appear in `#archiveNotice` (no silent catch). Close button works. Automatic refresh must not disrupt selection.
4. This GitHub/public edition: personal-only button absent; export unavailable even if environment variables are set. Do not add private integrations.
6. Preserve working WSL2 Docker engine + historical SQLite data. Do not call hosted extraction services, create accounts, delete backups, run `docker compose down -v`, or perform git commit/push.
7. Verify with offline Python tests and browser UI smoke test; document what was and wasn't actually tested.

Work only on this GitHub/public edition. Never commit private runtime or scraped data.
