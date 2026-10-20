"""FastAPI application factory: routers, middleware, errors and the Web entry."""
from __future__ import annotations

import logging
import re
import time
from collections import deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import comparison, documents, knowledge, research, system, workflows
from .logging_utils import configure_logging, get_trace_id, new_trace_id, set_trace_id
from .settings import settings
from .store import init_store

logger = logging.getLogger(__name__)

_RATE_LIMIT: dict[str, deque[float]] = {}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_TRACE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    init_store()
    logger.info("SpectraScholar starting version=%s backend=%s", settings.app_version, settings.research_backend)
    yield
    logger.info("SpectraScholar stopping")


def _rate_limited(client: str) -> bool:
    if settings.rate_limit_per_minute <= 0:
        return False
    now = time.monotonic()
    bucket = _RATE_LIMIT.setdefault(client, deque())
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        return True
    bucket.append(now)
    return False


def _error_payload(detail: object, code: str) -> dict:
    return {"detail": detail, "error_code": code, "trace_id": get_trace_id()}


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "SpectraScholar：科研文献调研与分析 Agent。"
            "通用网页研究能力来自 Apache-2.0 的 GPT Researcher；"
            "本地 PDF 抽取、证据核验、对比与混合检索为个人扩展模块。"
        ),
        lifespan=lifespan,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-API-Key", "X-Trace-ID"],
            expose_headers=["X-Trace-ID"],
        )

    @app.middleware("http")
    async def observability_and_rate_limit(request: Request, call_next):
        incoming = request.headers.get("X-Trace-ID", "")
        trace_id = incoming if _TRACE_RE.match(incoming) else new_trace_id()
        set_trace_id(trace_id)
        started = time.perf_counter()
        if request.method in _WRITE_METHODS:
            client = request.client.host if request.client else "unknown"
            if _rate_limited(client):
                response = JSONResponse(
                    status_code=429,
                    content=_error_payload("请求过于频繁，请稍后再试", "rate_limited"),
                )
                response.headers["Retry-After"] = "60"
                return response
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; connect-src 'self'; "
            "img-src 'self' data:; object-src 'none'; base-uri 'self'"
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "%s %s -> %s (%sms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        errors = [
            {
                "loc": list(error.get("loc", [])),
                "msg": error.get("msg", "invalid value"),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(status_code=422, content=_error_payload(errors, "validation_error"))

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(detail, f"http_{exc.status_code}"),
            headers=exc.headers or None,
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.exception("unhandled error path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=_error_payload("服务器内部错误，请查看服务日志", "internal_error"),
        )

    app.include_router(system.router)
    app.include_router(research.router)
    app.include_router(documents.router)
    app.include_router(comparison.router)
    app.include_router(knowledge.router)
    app.include_router(workflows.router)

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(settings.root / "web" / "index.html")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        return Response(status_code=204)

    return app


app = create_app()
