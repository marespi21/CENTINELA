"""Structured (JSON) logging for the Centinela API.

Every log record is emitted to stdout as a single-line JSON document so that a
log collector (Azure Monitor / Container Apps in later weeks) can index the
fields directly. Any keyword passed through ``logger.info(..., extra={...})``
is merged into the JSON payload.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

# Standard attributes present on every LogRecord. Anything outside this set was
# supplied by the caller via ``extra=`` and therefore belongs in the payload.
_RESERVED: set[str] = set(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Render a :class:`logging.LogRecord` as a single-line JSON document."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Merge structured extras (keys not part of the standard record).
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable single-line formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        line = (
            f"{timestamp} {record.levelname:<7} {record.name}: {record.getMessage()}"
        )
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _RESERVED and not key.startswith("_")
        }
        if extras:
            line += " | " + " ".join(f"{key}={value}" for key, value in extras.items())
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


_configured = False


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    """Install a log formatter on the root logger (idempotent).

    ``fmt`` is ``"console"`` (human-readable) or ``"json"`` (structured).
    """
    global _configured
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ConsoleFormatter() if fmt == "console" else JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # The Azure SDK logs every HTTP request/response (with headers) at INFO,
    # which floods local logs. Keep only its warnings and errors.
    logging.getLogger("azure").setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, configuring logging on first use."""
    if not _configured:
        configure_logging()
    return logging.getLogger(name)
