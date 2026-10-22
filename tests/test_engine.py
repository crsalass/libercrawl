import asyncio
import json
import httpx
import pytest
from app.engine import LocalEngineClient, EngineError


def test_engine_mock_scrape_and_health():
    seen = []
    def handler(req):
        seen.append((str(req.url), req.method))
        if req.url.path == "/v2/scrape" and req.content == b"{}":
            return httpx.Response(422, json={"success": False, "error": "Missing URL"})
        return httpx.Response(200, json={"success": True, "data":{"markdown":"# OK"}})
    eng = LocalEngineClient("http://127.0.0.1:3002", transport=httpx.MockTransport(handler))
    assert asyncio.run(eng.health())["healthy"]
    assert asyncio.run(eng.scrape("https://example.org"))["data"]["markdown"] == "# OK"
    assert all("127.0.0.1:3002" in url for url,_ in seen)


def test_engine_rejects_failure():
    eng = LocalEngineClient("http://localhost:3002", transport=httpx.MockTransport(lambda r: httpx.Response(200,json={"success":False,"error":"unsupported"})))
    with pytest.raises(EngineError, match="unsupported"):
        asyncio.run(eng.map("https://example.org", 10))
