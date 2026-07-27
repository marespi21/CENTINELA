"""Middleware de rate limiting por IP de origen (en memoria, sin Redis)."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.infrastructure.config.settings import Settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Limita requests por IP origen usando ventana deslizante en memoria.

    Si rate_limit_enabled es False, deja pasar todo sin contar.
    """

    def __init__(self, app: Callable[..., Awaitable[Response]], settings: Settings) -> None:
        super().__init__(app)
        self._enabled = settings.rate_limit_enabled
        self._max_requests = settings.rate_limit_max_requests
        self._window_seconds = settings.rate_limit_window_seconds
        # {ip: [timestamp, ...]}  — timestamps de requests en la ventana actual
        self._buckets: dict[str, list[float]] = defaultdict(list)

    @staticmethod
    def _client_ip(request: Request) -> str:
        """IP de origen real. Detrás de App Service/Front Door la IP del cliente
        viaja en `X-Forwarded-For` (primer valor); si no, la del peer directo."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        if not self._enabled:
            return await call_next(request)

        client_ip = self._client_ip(request)
        now = time.time()
        cutoff = now - self._window_seconds

        # Limpiar timestamps viejos para esta IP
        timestamps = self._buckets[client_ip]
        self._buckets[client_ip] = [t for t in timestamps if t > cutoff]

        if len(self._buckets[client_ip]) >= self._max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Try again later.",
                    "code": "RATE_LIMIT_EXCEEDED",
                },
            )

        self._buckets[client_ip].append(now)
        return await call_next(request)

