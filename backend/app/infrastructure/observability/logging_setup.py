"""Logs correlacionados con la traza (Sprint 6, Fase 3).

Un log suelto en producción sirve de poco: dice QUÉ pasó pero no en qué petición.
Al estampar `trace_id` y `span_id` en cada registro, cualquier línea de log lleva
al trace completo —y al revés— así que investigar un caso concreto deja de ser
arqueología sobre marcas de tiempo.

Formato JSON opcional (`LOG_FORMAT=json`): Container Apps recoge stdout y lo
manda a Log Analytics, donde un log estructurado se consulta por campos en vez
de con `contains`. En local se mantiene el formato de texto, que se lee mejor.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any


class TraceContextFilter(logging.Filter):
    """Añade `trace_id` y `span_id` al registro si hay una traza activa."""

    def filter(self, record: logging.LogRecord) -> bool:
        trace_id = "-"
        span_id = "-"
        try:
            from opentelemetry import trace

            span = trace.get_current_span()
            context = span.get_span_context() if span else None
            if context is not None and context.is_valid:
                # Formato hexadecimal de 32/16 dígitos: el mismo que usa
                # Application Insights, así que los identificadores se pueden
                # pegar tal cual en el portal.
                trace_id = format(context.trace_id, "032x")
                span_id = format(context.span_id, "016x")
        except Exception:  # noqa: BLE001 - sin OTel o sin traza activa
            pass

        record.trace_id = trace_id  # type: ignore[attr-defined]
        record.span_id = span_id  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    """Formatea el registro como una línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
            "span_id": getattr(record, "span_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(service_name: str) -> None:
    """Configura el logging raíz. Idempotente."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    use_json = os.getenv("LOG_FORMAT", "text").lower() == "json"

    handler = logging.StreamHandler()
    handler.addFilter(TraceContextFilter())
    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [trace=%(trace_id)s span=%(span_id)s] "
                "%(name)s %(message)s"
            )
        )

    root = logging.getLogger()
    # Se reemplazan los handlers en vez de añadir: llamar dos veces no puede
    # acabar duplicando cada línea de log.
    root.handlers = [handler]
    root.setLevel(level)
    logging.getLogger(__name__).debug("logging configurado para %s", service_name)
