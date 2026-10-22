"""Local SQLite persistence; no hosted database or telemetry."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, directory: str | Path):
        path = Path(directory).resolve()
        path.mkdir(parents=True, exist_ok=True)
        self.db = path / "embercrawl.sqlite3"
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY, kind TEXT NOT NULL, status TEXT NOT NULL,
                  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                  requested INTEGER NOT NULL DEFAULT 0, completed INTEGER NOT NULL DEFAULT 0,
                  error TEXT, args_json TEXT NOT NULL DEFAULT '{}', links_json TEXT NOT NULL DEFAULT '[]',
                  remote_id TEXT
                );
                CREATE TABLE IF NOT EXISTS pages (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  job_id TEXT NOT NULL REFERENCES jobs(id),
                  url TEXT NOT NULL, title TEXT,
                  markdown TEXT, html TEXT, links_json TEXT NOT NULL DEFAULT '[]',
                  metadata_json TEXT NOT NULL DEFAULT '{}', product_json TEXT NOT NULL DEFAULT '{}',
                  UNIQUE(job_id,url)
                );
                CREATE INDEX IF NOT EXISTS idx_pages_job ON pages(job_id);
            """)
            conn.execute("UPDATE jobs SET status='interrupted',error='App stopped before completion' WHERE status IN ('running','queued')")

    def connect(self):
        conn = sqlite3.connect(str(self.db), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def add_job(self, job_id: str, kind: str, args: dict, requested: int):
        with self.connect() as conn:
            conn.execute("INSERT INTO jobs (id,kind,status,args_json,requested) VALUES (?,?,?,?,?)",
                         (job_id, kind, "queued", json.dumps(args), requested))

    def update(self, job_id: str, **fields):
        allowed = {"status", "requested", "completed", "error", "links_json", "remote_id"}
        if not fields or set(fields) - allowed:
            raise ValueError("Invalid update fields")
        clauses = [f"{key}=?" for key in fields]
        with self.connect() as conn:
            conn.execute(f"UPDATE jobs SET {','.join(clauses)},updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",
                         [*fields.values(), job_id])

    def add_page(self, job_id: str, page: dict):
        metadata = page.get("metadata") if isinstance(page.get("metadata"), dict) else {}
        url = str(metadata.get("sourceURL") or metadata.get("url") or page.get("url") or "")
        if not url:
            raise ValueError("Scrape response missing page URL")
        from app.product import product_from_html
        # Unmodified raw HTML preserves JSON-LD scripts stripped from cleaned HTML.
        html = str(page.get("rawHtml") or page.get("html") or "")[:4_000_000]
        product = product_from_html(html, metadata, url)
        title = str(metadata.get("title") or product.get("name") or url)[:400]
        links = page.get("links") if isinstance(page.get("links"), list) else []
        with self.connect() as conn:
            conn.execute("""INSERT INTO pages(job_id,url,title,markdown,html,links_json,metadata_json,product_json)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(job_id,url) DO UPDATE SET
                title=excluded.title,markdown=excluded.markdown,html=excluded.html,
                links_json=excluded.links_json,metadata_json=excluded.metadata_json,product_json=excluded.product_json""",
                (job_id, url, title, str(page.get("markdown") or "")[:4_000_000], html,
                 json.dumps(links[:10000]), json.dumps(metadata), json.dumps(product)))

    def list_jobs(self, limit=75):
        with self.connect() as conn:
            return [self._job(dict(r)) for r in conn.execute("SELECT jobs.*, (SELECT COUNT(*) FROM pages p WHERE p.job_id=jobs.id) AS page_count FROM jobs ORDER BY jobs.created_at DESC LIMIT ?", (limit,))]

    def job(self, job_id: str) -> dict | None:
        with self.connect() as conn:
            row = conn.execute("SELECT jobs.*, (SELECT COUNT(*) FROM pages p WHERE p.job_id=jobs.id) AS page_count FROM jobs WHERE jobs.id=?", (job_id,)).fetchone()
            return self._job(dict(row)) if row else None

    def pages(self, job_id: str) -> list[dict]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM pages WHERE job_id=? ORDER BY id", (job_id,)).fetchall()
        result = []
        for r in rows:
            row = dict(r)
            for key in ("links_json", "metadata_json", "product_json"):
                row[key[:-5]] = json.loads(row.pop(key))
            result.append(row)
        return result

    def _job(self, row: dict) -> dict:
        row["args"] = json.loads(row.pop("args_json"))
        row["links"] = json.loads(row.pop("links_json"))
        return row
