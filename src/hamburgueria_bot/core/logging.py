
"""Infra de logging JSON usando structlog, com trace_id contextual."""
from __future__ import annotations
import structlog
import sys
from typing import Any
from uuid import uuid4
from contextvars import ContextVar

trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="-")

def set_trace_id(value: str | None = None) -> str:
    """Define trace_id no contexto atual e retorna o valor definido."""
    tid = value or uuid4().hex
    trace_id_ctx.set(tid)
    return tid

def get_logger() -> structlog.stdlib.BoundLogger:
    """Cria logger JSON com trace_id injetado automaticamente."""
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            lambda _, __, ev: {**ev, "trace_id": trace_id_ctx.get()},
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
    )
    return structlog.get_logger()
