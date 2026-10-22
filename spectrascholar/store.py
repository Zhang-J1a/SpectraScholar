"""SQLite persistence layer.

The project intentionally keeps a single-file SQLite database for local use.
Every function opens a short-lived connection, which is safe to call from
FastAPI background threads.  The schema is created and migrated in
:func:`init_store`, so an existing starter database keeps working.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from uuid import uuid4

from .schemas import ResearchRequest, WorkflowRequest
from .settings import settings


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _json_or_none(value: object) -> str | None:
    return None if value is None else json.dumps(value, ensure_ascii=False)


def _loads(value: str | None) -> object | None:
    if not value:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


class _ClosingConnection(sqlite3.Connection):
    """Commit/rollback on context exit *and* close the file handle.

    ``sqlite3.Connection``'s context manager does not close the connection.
    On Windows the unclosed handle blocks test cleanup and database replacement.
    """

    def __exit__(self, exc_type, exc, traceback):  # type: ignore[override]
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()


def connect() -> sqlite3.Connection:
    settings.ensure_directories()
    connection = sqlite3.connect(settings.db_path, timeout=30, factory=_ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    return {row["name"] for row in rows}


def _ensure_columns(connection: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = _columns(connection, table)
    for name, ddl in columns.items():
        if name not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_store() -> None:
    settings.ensure_directories()
    with connect() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                source TEXT NOT NULL,
                domain TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'zh',
                status TEXT NOT NULL,
                backend TEXT NOT NULL DEFAULT 'demo',
                is_demo INTEGER NOT NULL DEFAULT 1,
                error TEXT,
                error_type TEXT,
                report TEXT,
                citation_audit TEXT,
                metadata TEXT,
                trace_id TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                elapsed_ms INTEGER,
                max_elapsed_seconds INTEGER,
                max_cost_usd REAL,
                cancel_requested INTEGER NOT NULL DEFAULT 0
            )"""
        )
        _ensure_columns(
            connection,
            "jobs",
            {
                "language": "TEXT NOT NULL DEFAULT 'zh'",
                "backend": "TEXT NOT NULL DEFAULT 'demo'",
                "is_demo": "INTEGER NOT NULL DEFAULT 1",
                "error_type": "TEXT",
                "citation_audit": "TEXT",
                "metadata": "TEXT",
                "trace_id": "TEXT",
                "attempts": "INTEGER NOT NULL DEFAULT 0",
                "started_at": "TEXT",
                "elapsed_ms": "INTEGER",
                "max_elapsed_seconds": "INTEGER",
                "max_cost_usd": "REAL",
                "cancel_requested": "INTEGER NOT NULL DEFAULT 0",
            },
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS job_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                level TEXT NOT NULL,
                step TEXT NOT NULL,
                message TEXT NOT NULL,
                duration_ms INTEGER,
                created_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id, event_id)"
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS job_queue (
                job_id TEXT PRIMARY KEY,
                trace_id TEXT NOT NULL,
                request_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'queued',
                attempts INTEGER NOT NULL DEFAULT 0,
                available_at TEXT NOT NULL,
                locked_at TEXT,
                worker_id TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_job_queue_claim ON job_queue(status, available_at)"
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                size INTEGER NOT NULL,
                stored_name TEXT NOT NULL UNIQUE,
                sha256 TEXT,
                page_count INTEGER,
                title TEXT,
                created_at TEXT NOT NULL
            )"""
        )
        _ensure_columns(
            connection,
            "documents",
            {
                "sha256": "TEXT",
                "page_count": "INTEGER",
                "title": "TEXT",
                "created_at": "TEXT",
            },
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_documents_sha ON documents(sha256)")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS comparisons (
                comparison_id TEXT PRIMARY KEY,
                document_ids TEXT NOT NULL,
                extraction_mode TEXT NOT NULL,
                payload TEXT NOT NULL,
                markdown TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                document_ids TEXT NOT NULL,
                extraction_mode TEXT NOT NULL,
                language TEXT NOT NULL DEFAULT 'zh',
                status TEXT NOT NULL,
                current_step TEXT,
                comparison_id TEXT,
                report TEXT,
                citation_audit TEXT,
                error TEXT,
                trace_id TEXT,
                idempotency_key TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                elapsed_ms INTEGER
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_workflows_idem ON workflows(idempotency_key)"
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS workflow_steps (
                step_id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt INTEGER NOT NULL DEFAULT 0,
                input_summary TEXT,
                output_summary TEXT,
                error TEXT,
                started_at TEXT,
                finished_at TEXT,
                duration_ms INTEGER
            )"""
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_workflow_steps ON workflow_steps(workflow_id, step_id)"
        )


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
def create_job(req: ResearchRequest, backend: str, trace_id: str) -> str:
    job_id = str(uuid4())
    with connect() as connection:
        connection.execute(
            """INSERT INTO jobs(
                job_id,topic,source,domain,language,status,backend,is_demo,trace_id,attempts,created_at,
                max_elapsed_seconds,max_cost_usd
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                job_id,
                req.topic,
                req.source,
                req.domain,
                req.language,
                "queued",
                backend,
                1 if backend == "demo" else 0,
                trace_id,
                0,
                now_iso(),
                req.max_elapsed_seconds,
                req.max_cost_usd,
            ),
        )
    return job_id


def mark_job_running(job_id: str, attempt: int) -> None:
    with connect() as connection:
        connection.execute(
            """UPDATE jobs SET status='running', attempts=?,
               started_at=COALESCE(started_at, ?)
               WHERE job_id=? AND status!='cancelled'""",
            (attempt, now_iso(), job_id),
        )


def finish_job(
    job_id: str,
    status: str,
    report: str | None = None,
    error: str | None = None,
    error_type: str | None = None,
    citation_audit: dict | None = None,
    metadata: dict | None = None,
) -> None:
    with connect() as connection:
        row = connection.execute(
            "SELECT started_at, status, cancel_requested FROM jobs WHERE job_id=?",
            (job_id,),
        ).fetchone()
        if row is not None and row["status"] == "cancelled" and status != "cancelled":
            # Never overwrite a user cancellation with a late worker result.
            return
        if row is not None and row["cancel_requested"] and status != "cancelled":
            # A running job may finish just after the user clicked cancel.
            status = "cancelled"
            report = None
            error = "用户取消"
            error_type = "cancelled"
        elapsed_ms = None
        if row and row["started_at"]:
            try:
                started = datetime.fromisoformat(row["started_at"])
                elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            except ValueError:
                elapsed_ms = None
        connection.execute(
            """UPDATE jobs SET status=?, report=?, error=?, error_type=?, citation_audit=?,
               metadata=?, finished_at=?, elapsed_ms=? WHERE job_id=?""",
            (
                status,
                report,
                error,
                error_type,
                _json_or_none(citation_audit),
                _json_or_none(metadata),
                now_iso(),
                elapsed_ms,
                job_id,
            ),
        )


def request_job_cancel(job_id: str) -> dict | None:
    """Cooperative cancel: queued jobs are cancelled immediately; running jobs
    get a cancel flag checked by the worker at phase boundaries.
    """
    with connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT status FROM jobs WHERE job_id=?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        if row["status"] in {"completed", "failed", "cancelled"}:
            connection.rollback()
            return get_job(job_id)
        if row["status"] == "queued":
            connection.execute(
                """UPDATE jobs SET status='cancelled', cancel_requested=1,
                   finished_at=?, error=?, error_type='cancelled'
                   WHERE job_id=? AND status='queued'""",
                (now_iso(), "用户取消（尚未执行）", job_id),
            )
            connection.execute(
                """UPDATE job_queue SET status='cancelled', updated_at=?
                   WHERE job_id=? AND status='queued'""",
                (now_iso(), job_id),
            )
        else:
            connection.execute(
                "UPDATE jobs SET cancel_requested=1 WHERE job_id=?",
                (job_id,),
            )
        connection.commit()
    return get_job(job_id)


def is_cancel_requested(job_id: str) -> bool:
    with connect() as connection:
        row = connection.execute(
            "SELECT cancel_requested FROM jobs WHERE job_id=?", (job_id,)
        ).fetchone()
    return bool(row and row["cancel_requested"])


def add_job_event(
    job_id: str,
    level: str,
    step: str,
    message: str,
    duration_ms: int | None = None,
) -> None:
    with connect() as connection:
        connection.execute(
            """INSERT INTO job_events(job_id,level,step,message,duration_ms,created_at)
               VALUES(?,?,?,?,?,?)""",
            (job_id, level, step, message[:4000], duration_ms, now_iso()),
        )


def list_job_events(job_id: str, limit: int = 200) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM job_events WHERE job_id=? ORDER BY event_id ASC LIMIT ?",
            (job_id, min(max(limit, 1), 1000)),
        ).fetchall()
    return [dict(row) for row in rows]


def _job_row(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["is_demo"] = bool(data.get("is_demo"))
    data["cancel_requested"] = bool(data.get("cancel_requested"))
    data["citation_audit"] = _loads(data.get("citation_audit"))
    data["metadata"] = _loads(data.get("metadata"))
    return data


def get_job(job_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
    return _job_row(row) if row is not None else None


def recent_jobs(limit: int = 20, status: str | None = None, offset: int = 0) -> list[dict]:
    limit = min(max(limit, 1), 100)
    offset = max(offset, 0)
    columns = (
        "job_id,topic,source,domain,language,status,backend,is_demo,error,error_type,"
        "trace_id,attempts,created_at,started_at,finished_at,elapsed_ms,"
        "max_elapsed_seconds,max_cost_usd,cancel_requested"
    )
    with connect() as connection:
        if status:
            rows = connection.execute(
                f"SELECT {columns} FROM jobs WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            ).fetchall()
        else:
            rows = connection.execute(
                f"SELECT {columns} FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    return [_job_row(row) for row in rows]


def job_count(status: str | None = None) -> int:
    with connect() as connection:
        if status:
            row = connection.execute("SELECT COUNT(*) FROM jobs WHERE status=?", (status,)).fetchone()
        else:
            row = connection.execute("SELECT COUNT(*) FROM jobs").fetchone()
        return int(row[0])


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------
def add_document(
    filename: str,
    size: int,
    stored_name: str,
    sha256: str | None = None,
    page_count: int | None = None,
    title: str | None = None,
) -> str:
    document_id = str(uuid4())
    with connect() as connection:
        connection.execute(
            """INSERT INTO documents(
                document_id,filename,size,stored_name,sha256,page_count,title,created_at
            ) VALUES(?,?,?,?,?,?,?,?)""",
            (document_id, filename, size, stored_name, sha256, page_count, title, now_iso()),
        )
    return document_id


def get_document(document_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE document_id=?", (document_id,)
        ).fetchone()
    return dict(row) if row is not None else None


def get_document_by_sha(sha256: str) -> dict | None:
    if not sha256:
        return None
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM documents WHERE sha256=? ORDER BY rowid ASC LIMIT 1", (sha256,)
        ).fetchone()
    return dict(row) if row is not None else None


def list_documents() -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """SELECT document_id,filename,size,stored_name,sha256,page_count,title,created_at
               FROM documents ORDER BY rowid DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def delete_document(document_id: str) -> dict | None:
    document = get_document(document_id)
    if document is None:
        return None
    with connect() as connection:
        connection.execute("DELETE FROM documents WHERE document_id=?", (document_id,))
    return document


def document_count() -> int:
    with connect() as connection:
        return int(connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0])


# ---------------------------------------------------------------------------
# Comparisons
# ---------------------------------------------------------------------------
def save_comparison(
    document_ids: list[str],
    extraction_mode: str,
    payload: dict,
    markdown: str,
) -> str:
    comparison_id = str(uuid4())
    with connect() as connection:
        connection.execute(
            """INSERT INTO comparisons(
                comparison_id,document_ids,extraction_mode,payload,markdown,created_at
            ) VALUES(?,?,?,?,?,?)""",
            (
                comparison_id,
                json.dumps(document_ids),
                extraction_mode,
                json.dumps(payload, ensure_ascii=False),
                markdown,
                now_iso(),
            ),
        )
    return comparison_id


def get_comparison(comparison_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM comparisons WHERE comparison_id=?", (comparison_id,)
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["payload"] = _loads(data.get("payload"))
    data["document_ids"] = _loads(data.get("document_ids")) or []
    return data


def list_comparisons(limit: int = 20) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """SELECT comparison_id,document_ids,extraction_mode,created_at
               FROM comparisons ORDER BY created_at DESC LIMIT ?""",
            (min(max(limit, 1), 100),),
        ).fetchall()
    results = []
    for row in rows:
        data = dict(row)
        data["document_ids"] = _loads(data.get("document_ids")) or []
        results.append(data)
    return results


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------
def create_workflow(req: WorkflowRequest, trace_id: str) -> str:
    workflow_id = str(uuid4())
    with connect() as connection:
        connection.execute(
            """INSERT INTO workflows(
                workflow_id,topic,document_ids,extraction_mode,language,status,trace_id,
                idempotency_key,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                workflow_id,
                req.topic,
                json.dumps(req.document_ids),
                req.extraction_mode,
                req.language,
                "queued",
                trace_id,
                req.idempotency_key,
                now_iso(),
            ),
        )
    return workflow_id


def get_workflow_by_idempotency(key: str) -> dict | None:
    if not key:
        return None
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM workflows WHERE idempotency_key=? ORDER BY created_at DESC LIMIT 1",
            (key,),
        ).fetchone()
    return _workflow_row(row) if row is not None else None


def _workflow_row(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["document_ids"] = _loads(data.get("document_ids")) or []
    data["citation_audit"] = _loads(data.get("citation_audit"))
    return data


def get_workflow(workflow_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM workflows WHERE workflow_id=?", (workflow_id,)
        ).fetchone()
    if row is None:
        return None
    data = _workflow_row(row)
    data["steps"] = list_workflow_steps(workflow_id)
    return data


def mark_workflow_running(workflow_id: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE workflows SET status='running', started_at=COALESCE(started_at, ?) WHERE workflow_id=?",
            (now_iso(), workflow_id),
        )


def set_workflow_step(workflow_id: str, name: str) -> None:
    with connect() as connection:
        connection.execute(
            "UPDATE workflows SET current_step=? WHERE workflow_id=?", (name, workflow_id)
        )


def finish_workflow(
    workflow_id: str,
    status: str,
    report: str | None = None,
    comparison_id: str | None = None,
    citation_audit: dict | None = None,
    error: str | None = None,
) -> None:
    with connect() as connection:
        row = connection.execute(
            "SELECT started_at FROM workflows WHERE workflow_id=?", (workflow_id,)
        ).fetchone()
        elapsed_ms = None
        if row and row["started_at"]:
            try:
                started = datetime.fromisoformat(row["started_at"])
                elapsed_ms = int((datetime.now(UTC) - started).total_seconds() * 1000)
            except ValueError:
                elapsed_ms = None
        connection.execute(
            """UPDATE workflows SET status=?, report=?, comparison_id=?, citation_audit=?,
               error=?, finished_at=?, elapsed_ms=? WHERE workflow_id=?""",
            (
                status,
                report,
                comparison_id,
                _json_or_none(citation_audit),
                error,
                now_iso(),
                elapsed_ms,
                workflow_id,
            ),
        )


def add_workflow_step(
    workflow_id: str,
    name: str,
    status: str,
    attempt: int = 0,
    input_summary: str | None = None,
    output_summary: str | None = None,
    error: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    duration_ms: int | None = None,
) -> int:
    with connect() as connection:
        cursor = connection.execute(
            """INSERT INTO workflow_steps(
                workflow_id,name,status,attempt,input_summary,output_summary,error,
                started_at,finished_at,duration_ms
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                workflow_id,
                name,
                status,
                attempt,
                input_summary,
                output_summary,
                error,
                started_at,
                finished_at,
                duration_ms,
            ),
        )
        return int(cursor.lastrowid)


def finish_workflow_step(
    step_id: int,
    status: str,
    *,
    output_summary: str | None = None,
    error: str | None = None,
    duration_ms: int | None = None,
    attempt: int | None = None,
) -> None:
    with connect() as connection:
        if attempt is None:
            connection.execute(
                """UPDATE workflow_steps SET status=?, output_summary=?, error=?,
                   finished_at=?, duration_ms=? WHERE step_id=?""",
                (status, output_summary, error, now_iso(), duration_ms, step_id),
            )
        else:
            connection.execute(
                """UPDATE workflow_steps SET status=?, output_summary=?, error=?,
                   finished_at=?, duration_ms=?, attempt=? WHERE step_id=?""",
                (status, output_summary, error, now_iso(), duration_ms, attempt, step_id),
            )


def list_workflow_steps(workflow_id: str) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM workflow_steps WHERE workflow_id=? ORDER BY step_id ASC",
            (workflow_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def recent_workflows(limit: int = 20) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """SELECT workflow_id,topic,document_ids,status,current_step,comparison_id,
                      error,created_at,started_at,finished_at,elapsed_ms
               FROM workflows ORDER BY created_at DESC LIMIT ?""",
            (min(max(limit, 1), 100),),
        ).fetchall()
    results = []
    for row in rows:
        data = dict(row)
        data["document_ids"] = _loads(data.get("document_ids")) or []
        results.append(data)
    return results
