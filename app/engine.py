"""Small HTTP client that can only reach the local extraction API v2."""
from __future__ import annotations

import httpx
from app.security import validate_engine_url


class EngineError(RuntimeError):
    pass


class LocalEngineClient:
    def __init__(self, base_url: str, transport: httpx.AsyncBaseTransport | None = None):
        self.base_url = validate_engine_url(base_url)
        self.transport = transport

    async def request(self, method: str, path: str, data: dict | None = None) -> dict:
        if not path.startswith("/v2/") and path != "/test":
            raise ValueError("Only documented local local extraction endpoints are supported")
        try:
            async with httpx.AsyncClient(base_url=self.base_url, transport=self.transport,
                                          trust_env=False, timeout=httpx.Timeout(70.0, connect=5.0),
                                          follow_redirects=False) as client:
                response = await client.request(method, path, json=data)
                response.raise_for_status()
                body = response.json()
                if not isinstance(body, dict):
                    raise EngineError("The engine returned unexpected non-object JSON")
                if body.get("success") is False:
                    raise EngineError(str(body.get("error") or "Extraction operation failed"))
                return body
        except (httpx.HTTPError, ValueError) as exc:
            if isinstance(exc, EngineError):
                raise
            raise EngineError(f"Local engine request failed: {str(exc)[:350]}") from exc

    async def health(self):
        """Probe the real v2 scrape route without asking it to fetch a URL.

        The pinned local engine does not necessarily expose GET /test. An empty
        scrape request is rejected as invalid input (400/422) by a healthy API.
        """
        try:
            async with httpx.AsyncClient(base_url=self.base_url, transport=self.transport,
                                          trust_env=False, timeout=5.0, follow_redirects=False) as client:
                response = await client.post("/v2/scrape", json={})
                if response.status_code not in (400, 422):
                    raise EngineError(f"Unexpected Engine probe response: HTTP {response.status_code}")
                return {"healthy": True}
        except httpx.HTTPError as exc:
            raise EngineError(f"Local extraction engine is unavailable: {str(exc)[:250]}") from exc

    async def scrape(self, url: str):
        return await self.request("POST", "/v2/scrape", {"url": url, "formats": ["markdown", "html", "rawHtml", "links"],
                                                         "onlyMainContent": False})

    async def map(self, url: str, limit: int):
        return await self.request("POST", "/v2/map", {"url": url, "limit": limit, "includeSubdomains": False})

    async def crawl(self, url: str, limit: int, depth: int):
        return await self.request("POST", "/v2/crawl", {"url": url, "limit": limit,
             "maxDiscoveryDepth": depth, "allowExternalLinks": False,
             "scrapeOptions": {"formats": ["markdown", "html", "rawHtml", "links"], "onlyMainContent": False}})

    async def crawl_status(self, job_id: str):
        # Job ID is validated by caller as UUID-shaped, never an arbitrary path.
        return await self.request("GET", f"/v2/crawl/{job_id}")

    async def crawl_cancel(self, job_id: str):
        return await self.request("DELETE", f"/v2/crawl/{job_id}")
