# Dashboard regression checks

The dashboard tests run against a disposable copy of the public application. They do not validate the extraction engine or a Docker deployment.

## Run the checks

Use a disposable Python environment with `requirements-dev.txt` installed. Set `APP_DATA_DIR` to a disposable directory before running the Python suite:

```bash
export APP_DATA_DIR="$PWD/.local-backups/test-data"
python -m pytest -q
node --check app/static/app.js
```

The optional browser suite requires Python Playwright, an installed Microsoft Edge browser, and a local axe-core script for accessibility checks:

```bash
python -m pip install playwright
npm install --prefix .local-backups/ui-review/tooling --ignore-scripts --no-audit --no-fund axe-core postcss
python tests/browser_ui.py --axe .local-backups/ui-review/tooling/node_modules/axe-core/axe.min.js
```

Use `--channel chrome` for an installed Chrome browser. Add `--stress-only` for the focused resilience checks. Omitting `--axe` skips the accessibility audit. These tools are development dependencies; the dashboard loads no remote scripts or fonts.

The runner creates an isolated app copy, SQLite archive and browser profile under ignored `.local-backups/ui-review/`. It reserves a non-listening loopback socket for the engine endpoint and restricts browser requests to the preview origin. Existing runtime configuration and archives are not used. The preview server stops when the run finishes; detailed results and extra captures remain local.

## Coverage and limitations

The suite covers all five workflows at 1440, 1024, 768, 390 and 320 CSS pixels; request payloads; busy, error and recovery states; first/last Inspect focus and scrolling; polling focus retention; fixture downloads and cancellation; long content; partial map entries; keyboard scrolling; reduced motion, reduced transparency, increased contrast, forced colors and touch emulation. Its fixtures are synthetic and never fetched from target websites.

Axe checks WCAG 2 A/AA and 2.1/2.2 AA rules. Gradient backgrounds and clipped scroll content can require manual contrast review even when there are no automatic violations. Automated checks do not establish full accessibility conformance. Physical phone input, screen readers, Safari/Firefox, native zoom and text-only enlargement require separate testing. The 720 × 540 CSS-pixel reflow check models a 200% zoom viewport; it does not control browser zoom.

No new isolated live-engine extraction, Docker build or Linux/WSL2 installation validation accompanies this UI update. Run the [first extraction check](../README.md#verify-your-first-extraction) on a disposable full installation. Existing security and extraction limitations remain in the [README](../README.md#security-and-limitations).

## Screenshots

Add `--capture` only to deliberately refresh the three after screenshots. Review the images before publishing and update [their provenance](assets/README.md) and the checksum manifest. The README image must show the actual public dashboard, with its real offline/empty state; populated inspector examples must visibly disclose test fixtures.
