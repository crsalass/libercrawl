"""Local web app for scraping, mapping, crawling and exporting without cloud APIs."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import re
import uuid
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.engine import EngineError, LocalEngineClient
from app.security import validate_target
from app.storage import Store

ROOT = Path(__file__).resolve().parent.parent
# Minimal .env parser (no external configuration service or network access).
local_env = ROOT / ".env"
if local_env.is_file():
    for raw_line in local_env.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            if re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
                os.environ.setdefault(key, value.strip().strip('"').strip("'"))
DATA_DIR = Path(os.getenv("APP_DATA_DIR", str(ROOT / "data")))
MAX_BATCH = min(100, max(1, int(os.getenv("MAX_BATCH_URLS", "30"))))
MAX_CRAWL = min(250, max(1, int(os.getenv("MAX_CRAWL_PAGES", "50"))))
MAX_SECONDS = max(60, min(3600, int(os.getenv("MAX_JOB_SECONDS", "900"))))
ENGINE_URL = os.getenv("LOCAL_ENGINE_URL", "http://127.0.0.1:3002")


store = Store(DATA_DIR)
engine = LocalEngineClient(ENGINE_URL)
active: dict[str, asyncio.Task] = {}
semaphore = asyncio.Semaphore(2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    for task in list(active.values()):
        task.cancel()
    for task in list(active.values()):
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Libercrawl Studio", description="Open-source local dashboard for self-hosted upstream engine", lifespan=lifespan,
              docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")


class URLRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def check_url(cls, value: str):
        # Syntactic preflight; a fresh DNS check occurs immediately before the fetch.
        return validate_target(value, resolve_dns=False)


class MapRequest(URLRequest):
    limit: int = Field(default=30, ge=1, le=250)


class CrawlRequest(URLRequest):
    limit: int = Field(default=10, ge=1, le=250)
    depth: int = Field(default=2, ge=0, le=6)


class BatchRequest(BaseModel):
    urls: list[str] = Field(min_length=1)

    @field_validator("urls")
    @classmethod
    def check_urls(cls, value: list[str]):
        if len(value) > MAX_BATCH:
            raise ValueError(f"Max {MAX_BATCH} URLs per batch")
        return list(dict.fromkeys(validate_target(url, resolve_dns=False) for url in value))


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/api/status")
async def status():
    try:
        await engine.health()
        ready, error = True, None
    except (EngineError, OSError) as exc:
        ready, error = False, str(exc)
    return {"app": "ready", "engine": "online" if ready else "offline",
            "backend": engine.base_url, "engine_error": error,
            "features": ["scrape", "batch", "crawl", "map", "sqlite", "exports", "jsonld-product"]}


def queue(kind: str, args: dict, amount: int) -> dict:
    job_id = str(uuid.uuid4())
    store.add_job(job_id, kind, args, amount)
    task = asyncio.create_task(worker(job_id, kind, args))
    active[job_id] = task
    task.add_done_callback(lambda _task: active.pop(job_id, None))
    return {"id": job_id, "status": "queued", "kind": kind}


@app.post("/api/scrape", status_code=202)
async def scrape(req: URLRequest):
    return queue("scrape", req.model_dump(), 1)


@app.post("/api/batch", status_code=202)
async def batch(req: BatchRequest):
    return queue("batch", req.model_dump(), len(req.urls))


@app.post("/api/crawl", status_code=202)
async def crawl(req: CrawlRequest):
    if req.limit > MAX_CRAWL:
        raise HTTPException(422, f"Max crawl pages is {MAX_CRAWL}")
    return queue("crawl", req.model_dump(), req.limit)


@app.post("/api/map", status_code=202)
async def map_site(req: MapRequest):
    return queue("map", req.model_dump(), req.limit)


@app.get("/api/jobs")
async def jobs():
    return {"jobs": store.list_jobs()}


@app.get("/api/jobs/{job_id}")
async def job(job_id: uuid.UUID):
    record = store.job(str(job_id))
    if not record:
        raise HTTPException(404, "Job not found")
    previews = store.pages(str(job_id))
    for page in previews:
        page["html"] = None  # full page retained in SQLite / export only
        page["markdown"] = page["markdown"][:6000]
    return {**record, "pages": previews}


@app.post("/api/jobs/{job_id}/cancel")
async def cancel(job_id: uuid.UUID):
    jid = str(job_id)
    record = store.job(jid)
    if not record:
        raise HTTPException(404, "Job not found")
    if record["status"] in ("completed", "failed", "cancelled", "interrupted"):
        raise HTTPException(409, "Job has already stopped")
    task = active.get(jid)
    if task:
        task.cancel()
    else:
        store.update(jid, status="cancelled", error="Cancelled by user")
    return {"status": "cancelling"}


async def worker(job_id: str, kind: str, args: dict):
    try:
        async with semaphore:
            store.update(job_id, status="running")
            await asyncio.wait_for(dispatch(job_id, kind, args), timeout=MAX_SECONDS)
            store.update(job_id, status="completed")
    except asyncio.CancelledError:
        remote = store.job(job_id).get("remote_id")
        if remote:
            with suppress(Exception):
                await engine.crawl_cancel(remote)
        store.update(job_id, status="cancelled", error="Cancelled")
        raise
    except Exception as exc:
        store.update(job_id, status="failed", error=(f"{type(exc).__name__}: {exc}")[:700])


async def scrape_one(job_id: str, url: str):
    checked = await asyncio.to_thread(validate_target, url)
    body = await engine.scrape(checked)
    data = body.get("data")
    if not isinstance(data, dict):
        raise EngineError("Scrape response has no document object")
    data.setdefault("metadata", {})
    if isinstance(data["metadata"], dict):
        data["metadata"].setdefault("sourceURL", checked)
    store.add_page(job_id, data)


async def dispatch(job_id: str, kind: str, args: dict):
    if kind == "scrape":
        await scrape_one(job_id, args["url"])
        store.update(job_id, completed=1)
    elif kind == "batch":
        errors = []
        for index, url in enumerate(args["urls"], start=1):
            try:
                await scrape_one(job_id, url)
            except (EngineError, ValueError) as exc:
                errors.append(f"{url}: {str(exc)[:160]}")
            store.update(job_id, completed=index)
        if errors:
            store.update(job_id, error="; ".join(errors)[:700])
        if len(errors) == len(args["urls"]):
            raise EngineError("All batch URLs failed: " + "; ".join(errors)[:400])
    elif kind == "map":
        checked = await asyncio.to_thread(validate_target, args["url"])
        body = await engine.map(checked, args["limit"])
        extra = body.get("data")
        links = body.get("links") or (extra.get("links") if isinstance(extra, dict) else None)
        if not isinstance(links, list):
            raise EngineError("Map response has no links array")
        store.update(job_id, links_json=json.dumps(links[:args["limit"]]), completed=min(len(links), args["limit"]))
    elif kind == "crawl":
        checked = await asyncio.to_thread(validate_target, args["url"])
        launch = await engine.crawl(checked, args["limit"], args["depth"])
        remote_id = launch.get("id")
        if not isinstance(remote_id, str) or not re.fullmatch(r"[a-fA-F0-9-]{36}", remote_id):
            raise EngineError("Crawl response missing valid crawl ID")
        store.update(job_id, remote_id=remote_id)
        seen = set()
        while True:
            state = await engine.crawl_status(remote_id)
            docs = state.get("data") or []
            if isinstance(docs, list):
                for page in docs:
                    if not isinstance(page, dict):
                        continue
                    meta = page.get("metadata", {})
                    address = (meta.get("sourceURL") if isinstance(meta, dict) else None) or page.get("url")
                    if not address or address in seen or len(seen) >= args["limit"]:
                        continue
                    seen.add(address)
                    store.add_page(job_id, page)
            store.update(job_id, completed=len(seen))
            progress = state.get("status")
            if progress in ("completed", "failed", "cancelled"):
                if progress != "completed":
                    raise EngineError(f"Crawl finished with status {progress}")
                # local extraction API v2 may paginate completed crawl data; for safety we
                # do not follow untrusted `next` links to a remote host.
                return
            await asyncio.sleep(2.5)
    else:
        raise ValueError("Unknown job kind")


def _export(job_record: dict, pages: list[dict], fmt: str):
    if fmt == "json":
        payload = {"job": job_record, "pages": pages}
        return json.dumps(payload, ensure_ascii=False, indent=2), "application/json", "json"
    if fmt == "jsonl":
        return "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in pages), "application/x-ndjson", "jsonl"
    if fmt == "markdown":
        result = "\n\n---\n\n".join(f"# {p['title']}\n\nSource: {p['url']}\n\n{p['markdown']}" for p in pages)
        return result, "text/markdown", "md"
    if fmt == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["url", "name", "brand", "sku", "price", "currency", "sizes", "colors", "material", "missing_fields"])
        for p in pages:
            product = p["product"]
            writer.writerow([p["url"], product.get("name"), product.get("brand"), product.get("sku"),
                             product.get("price"), product.get("currency"), " | ".join(product.get("sizes", [])),
                             " | ".join(product.get("color", [])), product.get("material"),
                             " | ".join(product.get("missing_fields", []))])
        return out.getvalue(), "text/csv", "csv"
    raise HTTPException(400, "Unsupported export format")


@app.get("/api/jobs/{job_id}/export")
async def export(job_id: uuid.UUID, format: Literal["json", "jsonl", "markdown", "csv"] = Query("json")):
    jid = str(job_id)
    job_record = store.job(jid)
    if not job_record:
        raise HTTPException(404, "Job not found")
    pages = store.pages(jid)
    if job_record["kind"] == "map" and format != "json":
        raise HTTPException(400, "Map URL lists can be exported as JSON only")
    content, content_type, ext = _export(job_record, pages, format)
    return Response(content=content, media_type=content_type,
                    headers={"Content-Disposition": f'attachment; filename="libercrawl-{jid[:8]}.{ext}"',
                             "X-Content-Type-Options": "nosniff"})
