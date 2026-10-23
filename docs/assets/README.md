# Dashboard screenshot provenance

The after captures show the current redesigned interface and final palette. Original before captures remain unchanged. The two `ui-before-final-*` files preserve the previous refinement's authentic after captures. Additional test evidence remains local.

All images below are authentic browser captures of the **public edition**, taken on **2026-10-23**. No generative images, compositing, retouching, invented production jobs, or personal installation were used.

| Asset | Size | State |
| --- | --- | --- |
| [`public-dashboard.png`](public-dashboard.png) | 1440 × 1420 PNG; about 258 KiB | Final palette/background, Single scrape, empty archive, engine offline. This is the README image. |
| [`ui-before-desktop.png`](ui-before-desktop.png) | 1440 × 1261 PNG | Original dashboard before the redesign, empty archive, engine offline. Preserves the original screenshot. |
| [`ui-before-mobile.png`](ui-before-mobile.png) | 390 × 1515 PNG | Original mobile dashboard, empty archive, engine offline. |
| [`ui-before-final-desktop.png`](ui-before-final-desktop.png) | 1440 × 1369 PNG | Previous refinement, before the final palette/background pass; empty archive and offline engine. |
| [`ui-before-final-mobile.png`](ui-before-final-mobile.png) | 390 × 1330 PNG | Previous refinement's mobile capture, before the final visual pass. |
| [`ui-after-mobile.png`](ui-after-mobile.png) | 390 × 1374 PNG | Final mobile dashboard, empty archive, engine offline. |
| [`ui-after-inspect.png`](ui-after-inspect.png) | 1440 × 1080 PNG | Final Archive/Inspect with **explicit UI test fixtures**, not live extraction results. |

## Capture method

The after images come directly from [`tests/browser_ui.py`](../../tests/browser_ui.py), using the actual [`app/static/`](../../app/static/) files and unchanged public FastAPI backend on `ui/apple-like-polish`. The before images were captured from the pre-redesign public source in a separate isolated preview. All use headless Microsoft Edge **155.0.4283.62**, Playwright **1.64.1**, device scale 1, local system fonts, `en-GB`, and `Europe/Madrid`. Desktop and mobile full-page captures use 1080-pixel-high viewports; the inspector image captures the current viewport after scrolling to the archive.

Each preview copies only public `app/` into a new disposable directory inside this checkout, omits runtime configuration, and uses a new SQLite archive. The engine endpoint is a reserved, non-listening loopback port, preventing contact with an existing engine. The browser is restricted to its isolated dashboard origin. No extraction engine, Docker stack, hosted extraction API, Ubuntu/WSL installation, private database, or existing runtime archive was accessed by the preview. Existing `engine/`, `data/`, `.venv`, `.env`, and Docker volumes were not modified.

The README and before/after dashboard captures are taken **before any fixture is inserted**. The inspector image is separate and visibly says **“UI test fixture — no live extraction”**; its content explicitly states that no website was fetched. Fixture running/completed states exist only to exercise UI controls. Mocked online status and accepted/error requests are used only in tests, not in the README screenshot.

The PNG files are native browser output, with no semantic image edits, additional design assets, or remote fonts. The README image is approximately 258 KiB at native resolution; its atmospheric gradients account for the increase from the flatter earlier image. Original pixels are preserved rather than resampled. The images follow the repository's [license scope](../../LICENSE_SCOPE.md); exact binary hashes are recorded in [`SHA256SUMS.txt`](../../SHA256SUMS.txt).

See [dashboard regression checks](../UI_TESTING.md) for reproduction commands, coverage, and limitations. Temporary previews and additional tablet/mobile review evidence stay in the ignored `.local-backups/ui-review/` directory. Preview servers are stopped after each run.
