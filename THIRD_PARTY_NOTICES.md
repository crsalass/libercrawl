# Third-party notices and source provenance

This notice is provided for attribution, reproducibility, and license compliance. It is **not** product branding or a claim of affiliation. Keep it in public source distributions.

## Separately downloaded extraction engine

- **Original project:** Firecrawl, maintained by its respective copyright holders and contributors.
- **Upstream source:** https://github.com/firecrawl/firecrawl
- **Pinned tag:** `v2.11.0`
- **Pinned commit:** `ef12eb36b2f3382838dfe0a0c1a5add3d5df7fe5`
- **Version-matched source:** [Firecrawl at the pinned commit](https://github.com/firecrawl/firecrawl/tree/ef12eb36b2f3382838dfe0a0c1a5add3d5df7fe5).
- **Acquisition:** `scripts/install.sh` or `scripts/install.ps1` clones the source into the untracked `engine/` directory. The source is *not bundled* in this repository.
- **Licenses:** The upstream repository states that it is primarily AGPL-3.0, with some components under MIT and potentially other licenses. Consult the actual `LICENSE` and component-specific license files in the checked-out version.
- **Modification:** Both installers and start scripts use [`scripts/patch_engine.py`](scripts/patch_engine.py), through `scripts/patch-engine.sh` on Linux, to update only RabbitMQ's health check in `engine/docker-compose.yaml`. The diagnostic runs under the `rabbitmq` user through `gosu`; interval and timeout change from 5 to 10 seconds, retries from 3 to 10, and startup grace from 5 to 120 seconds. The patch addresses cookie-permission and slow-start failures, is idempotent, and rejects unexpected layouts. This local compatibility change is documented on **2026-10-23**. The original engine's attribution and license terms remain unchanged.
- **Corresponding source:** The exact upstream commit is public at the link above; the complete text of the local compatibility modification is in the installation scripts in this repository. If you distribute a prebuilt modified engine or offer a modified version over a network, confirm that your method of providing complete corresponding source satisfies the AGPL obligations.

This project is an **independent user interface**, not an official product of the upstream project and not endorsed by its maintainers. Upstream names are used only to identify factual dependencies.

## Other dependencies

The application also uses FastAPI, Uvicorn, HTTPX, Beautiful Soup, Pydantic, Docker/Compose, Playwright/Chromium, Redis, RabbitMQ, PostgreSQL, and optional FoundationDB components from third-party sources. These components and their dependencies retain their own applicable licenses. The source distribution does not bundle their complete binaries, and this summary is **not a comprehensive dependency SBOM or legal clearance**. Before redistributing binaries or container images, create a version-resolved software bill of materials, review each license and NOTICE, and preserve applicable notices.

## No affiliation

The Libercrawl name, UI and documentation are not sponsored, supported or officially endorsed by the upstream engine maintainers or by other vendors mentioned in installation instructions.
