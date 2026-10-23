# User Guide

Libercrawl runs in your browser at `http://127.0.0.1:3210` and sends work to the local extraction engine at `http://127.0.0.1:3002`, both bound to the local computer by default.

## Using the dashboard

### Single scrape

Enter one public HTTP/HTTPS URL and submit. The local engine requests the page and returns structured scraped content. The dashboard stores available Markdown, HTML, metadata, links, and deterministic product candidates in SQLite.

### Batch scrape

Paste one URL per line. The app **sequentially** submits these as individual extraction requests inside one job; it does **not** call a remote batch API. The default limit is **30 URLs** per batch (a configurable maximum, hard-capped at 100 in backend code). Duplicate URLs in one batch are removed.

The batch may finish with partial results and a job error message for failed individual URLs. Review Archive → Inspect to understand which pages were collected.

### Crawl site

Provide a starting website URL and choose a page limit and discovery depth. The app runs a bounded crawl on the local extraction backend; external links are disallowed in the submitted options. The form defaults to **10 pages** and **depth 2**. The UI permits up to **50 pages**; the default backend cap is also 50. The UI/backend supports depth **0 to 6**. The configurable backend crawl cap cannot exceed 250 pages; changing it does not change the UI's 50-page input maximum.

Current limitation: Libercrawl does **not** follow `next` pagination links in the final engine crawl response, so large crawls may not archive every returned page. It stores unique pages by URL **within each job**, not globally across all jobs.

### Map URLs

Provide a domain or webpage to discover URLs. By default, the UI requests **30 discovered links**; up to **250** may be requested. The URL list is stored on the job record instead of as full scraped pages. Map jobs are exported as **JSON only**.

## Archive and Inspect

Every operation appears in **Archive** with its kind, status, progress, creation time, and an **Inspect** button. Inspect opens an accessible detail area with page previews, extracted product hints, completed counts, and reported errors. It also shows a visible message if details cannot be loaded.

The Archive list displays the latest **75 job summaries**. Its operation and saved-page counters summarize this list, not the entire database. Older jobs remain in SQLite; this is a display-query limit, not a retention policy. There is no archive-deletion control in the dashboard.

The archive is stored at `data/embercrawl.sqlite3` (the legacy filename is deliberately retained for compatibility). By default, scraped HTML and Markdown content are capped at **4 million characters** per page when stored, and Inspect previews display up to **6,000 Markdown characters** per page. Exports can include more stored content than the Inspect preview.

## Exports

| Format | Content | Notes |
| --- | --- | --- |
| **JSON** | Job metadata and all stored pages, including HTML, Markdown, links, metadata, and product candidates | Works for all job kinds; map URLs are in the job's `links` array. |
| **JSONL** | One JSON object per scraped page | For non-map jobs. |
| **Markdown** | Readable Markdown text for stored pages | For non-map jobs. |
| **CSV** | One row per page with product-oriented columns | For non-map jobs; useful for inspection, not a guaranteed product catalog. |

The CSV includes URL, name, brand, SKU, price, currency, sizes, colors, material, and missing-field indicators. It is a **candidate export**, not a verified commerce feed. Scraped cell values are not sanitized against spreadsheet-formula injection; import as text and review untrusted exports before opening them in a spreadsheet. HTML is available inside JSON/JSONL page records, not as a standalone HTML download.

## Product hints

Libercrawl attempts to read `schema.org`-style Product/ProductGroup JSON-LD and page metadata. It may detect product name, brand, SKU, category, material, price, currency, availability, images, colors, sizes, and variants when the page supplies them. It labels a best-effort extraction method and marks missing fields. It does not infer clothing fit: `fit` is currently unspecified.

It does not use a model to fill missing fields. A product page may yield sparse data if the website relies on JavaScript, hides variants, or omits structured metadata. Always validate against the source before publishing product information.

## Limits and cancellation

- At most **two Libercrawl jobs** execute concurrently in the dashboard worker semaphore.
- `MAX_JOB_SECONDS` defaults to **900 seconds**; effective allowed values are **60–3,600 seconds**.
- Batch jobs process URLs one after another; errors are recorded against the job.
- Cancel can interrupt an in-process job and attempts to cancel an engine-side crawl when a crawl ID is available.
- Dashboard process restarts mark queued or running jobs as **interrupted**. They are not resumed automatically.

## Supported URLs

The dashboard accepts public HTTP and HTTPS domains with standard ports (80/443). It blocks direct IP-address targets, common private/special-use hostnames, credentials in URLs, and fragments. This is a basic safety check, not a security boundary suitable for exposing the application to untrusted users.

## First smoke test

1. Check that **Engine online** appears.
2. Scrape `https://example.org`.
3. Open **Archive** and select **Inspect** for the new job.
4. Verify text extraction and export JSON or Markdown.

If the job fails, see [Troubleshooting](TROUBLESHOOTING.md) and inspect `docker logs --tail 100 embercrawl-engine-api-1`.
