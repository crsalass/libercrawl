# Pre-publication risk review — action items

Review date: **2026-10-23**. This is a technical and documentary risk review, **not legal advice or a trademark clearance opinion**. It covers the source package examined, not external deployment or future dependencies.

## Open issue: similar name used by another crawler

Another project publicly identifies itself as **LibreCrawl**, operates at https://librecrawl.com/, and has a GitHub repository at https://github.com/PhialsBasement/LibreCrawl. This release has been renamed to **Libercrawl**, but the spelling remains similar and both tools are web crawlers. The change reduces exact-name overlap; it does **not** establish trademark clearance or eliminate the possibility of confusion.

**Action:** assess whether **Libercrawl** is sufficiently distinguishable before release; seek competent trademark/name-clearance advice if needed. Search relevant EUIPO, national, and other applicable trademark registries; do not assume name availability from a GitHub repository or domain. No registry-wide clearance was conducted.

## License and attribution — addressed in documentation; ongoing obligation

- The prior root `LICENSE` was only a short notice; it has been replaced with the **full, unmodified GNU AGPLv3 text**.
- Original engine source, pinned commit, licensing and our RabbitMQ health-check change are disclosed in `THIRD_PARTY_NOTICES.md`. We do not claim authorship of the third-party engine.
- Removing required notices or pretending the engine is an original Libercrawl implementation would increase, rather than reduce, license and misrepresentation risks.
- This package downloads its engine during installation and does not contain its source checkout, compiled containers or binaries. If distributing a prebuilt system or offering a modified AGPL engine to remote users, re-check corresponding-source obligations, applicable notices and distribution license compatibility.
- Python dependency version ranges and container image tags are **not a complete version-pinned SBOM**. Before binary redistribution or professional deployment, resolve exact versions, scan known vulnerabilities and audit dependency licenses and notices.

## Web scraping and data protection — user responsibility

Do not describe the project as a way to bypass access controls, CAPTCHAs or websites' permissions. Websites can have terms, rate limits, copyrights, database rights and robots policies. Personal data handling may engage GDPR and other privacy laws. Have an appropriate legal basis and retention policy before collecting personal information. Respect site policies and refrain from gathering credentials, private, restricted or sensitive content. No legal review of target websites was performed.

## Security and privacy — local-only, not production hardened

- The frontend has no login; the local API uses an unauthenticated backend. Treat any LAN/public deployment as unsafe without additional independent design/review.
- Domain checks help reject private targets, but they do **not** guarantee protection against DNS rebinding, redirects, proxy misconfiguration, or other SSRF techniques.
- The application sends outbound requests to target websites; those sites and network intermediaries can observe requests. No blanket claim that all information remains on-device is appropriate.
- Local SQLite stores scraped pages and may contain sensitive/personal content. Set retention/backup controls and protect filesystem access.
- Runtime `.env`, keys, scraped archives, engine source/build outputs, and Docker volumes must remain untracked.

## Accuracy, branding and support

- Distinguish local dashboard behavior from features of the external engine and any hosted services.
- Hardware estimates are not certified minimums. Linux/WSL2 is the tested path; macOS/native Windows claims are experimental.
- Avoid implying affiliation/endorsement by upstream authors, Apple, or any other vendor.
- Keep `THIRD_PARTY_NOTICES.md` in every source release.
- Existing internal identifiers such as `embercrawl-engine` and `embercrawl.sqlite3` are compatibility details; do not advertise them as independent products.

## Before publication

1. Review the remaining name similarity risk; the rename alone is not a trademark clearance.
2. Obtain legal review if you need high-confidence advice on trademark, copyright, software licenses, or scraping jurisdiction.
3. Run offline tests and a real end-to-end local scrape.
4. Review the exact staged Git diff, secrets and third-party notices.
5. Decide if you are distributing **source-only** or prebuilt containers, because obligations differ.
