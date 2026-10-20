"""Small SQLite store for local demo. Replace with PostgreSQL + workers in production."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from .settings import settings
from .schemas import ResearchRequest


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    settings.workspace.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(settings.db_path, timeout=30)
    c.row_factory = sqlite3.Row
    return c


def init_store() -> None:
    settings.paper_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("""CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY, topic TEXT NOT NULL, source TEXT NOT NULL,
            domain TEXT NOT NULL, status TEXT NOT NULL, error TEXT, report TEXT,
            created_at TEXT NOT NULL, finished_at TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY, filename TEXT NOT NULL,
            size INTEGER NOT NULL, stored_name TEXT NOT NULL
        )""")


def create_job(req: ResearchRequest) -> str:
    job_id = str(uuid4())
    with connect() as c:
        c.execute("INSERT INTO jobs(job_id,topic,source,domain,status,created_at) VALUES(?,?,?,?,?,?)",
                  (job_id, req.topic, req.source, req.domain, "queued", _now()))
    return job_id


def update_job(job_id: str, status: str, report: str | None = None, error: str | None = None) -> None:
    with connect() as c:
        c.execute("UPDATE jobs SET status=?, report=?, error=?, finished_at=? WHERE job_id=?",
                  (status, report, error, _now() if status in ("completed", "failed") else None, job_id))


def get_job(job_id: str) -> dict | None:
    with connect() as c:
        r = c.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    return dict(r) if r is not None else None


def recent_jobs(limit: int = 20) -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (min(limit, 100),)).fetchall()
    return [dict(r) for r in rows]


def add_document(filename: str, size: int, stored_name: str) -> str:
    doc_id = str(uuid4())
    with connect() as c:
        c.execute("INSERT INTO documents(document_id,filename,size,stored_name) VALUES(?,?,?,?)",
                  (doc_id, filename, size, stored_name))
    return doc_id


def get_document(doc_id: str) -> dict | None:
    with connect() as c:
        r = c.execute("SELECT * FROM documents WHERE document_id=?", (doc_id,)).fetchone()
    return dict(r) if r is not None else None


def list_documents() -> list[dict]:
    with connect() as c:
        rs = c.execute("SELECT document_id,filename,size FROM documents ORDER BY rowid DESC").fetchall()
    return [dict(r) for r in rs]
