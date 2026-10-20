"""Structured application logging with a request-scoped trace id."""
from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar

from .settings import settings

_trace_id: ContextVar[str] = ContextVar("trace_id", default="-")


def new_trace_id() -> str:
    return uuid.uuid4().hex[:16]


def set_trace_id(trace_id: str | None = None) -> str:
    value = (trace_id or new_trace_id())[:64]
    _trace_id.set(value)
    return value


def get_trace_id() -> str:
    return _trace_id.get()


class TraceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": getattr(record, "trace_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_spectrascholar_configured", False):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(TraceFilter())
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(trace_id)s] %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )
    root.handlers = [handler]
    root.setLevel(getattr(logging, settings.log_level, logging.INFO))
    root._spectrascholar_configured = True  # type: ignore[attr-defined]
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
