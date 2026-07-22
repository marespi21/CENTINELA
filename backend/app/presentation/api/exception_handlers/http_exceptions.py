from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    # Seguridad: devolver error consistente, sin stacktrace.
    # Pydantic/FastAPI genera lista de errores; resumimos.
    first = exc.errors()[0] if exc.errors() else None
    detail = first.get("msg") if first else "Invalid request"

    return JSONResponse(
        status_code=400,
        content={"detail": detail, "code": "BAD_REQUEST"},
    )

