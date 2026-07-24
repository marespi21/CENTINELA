"""Tests para el middleware de rate limiting."""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure.config.settings import Settings
from app.presentation.api.middlewares.rate_limit import RateLimitMiddleware


def _build_app(settings: Settings | None = None) -> FastAPI:
    """Helper: crea app limpia con el middleware y un endpoint de prueba."""
    if settings is None:
        settings = Settings()

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, settings=settings)

    @app.get("/test")
    def test_endpoint() -> dict[str, str]:
        return {"status": "ok"}

    return app


class TestRateLimitMiddleware:
    """Suite de tests para el rate limiter en memoria."""

    def test_rate_limit_exceeded(self) -> None:
        """N+1 requests dentro de la ventana → 429."""
        settings = Settings(
            rate_limit_enabled=True,
            rate_limit_max_requests=3,
            rate_limit_window_seconds=60,
        )
        app = _build_app(settings)
        client = TestClient(app)

        # Los primeros 3 deben ser 200
        for _ in range(3):
            resp = client.get("/test")
            assert resp.status_code == 200, f"Esperado 200, obtuvo {resp.status_code}"

        # El 4to debe superar el límite → 429
        resp = client.get("/test")
        assert resp.status_code == 429
        body = resp.json()
        assert body["code"] == "RATE_LIMIT_EXCEEDED"
        assert "detail" in body

    def test_rate_limit_resets_after_window(self) -> None:
        """Pasada la ventana, vuelve a aceptar requests."""
        settings = Settings(
            rate_limit_enabled=True,
            rate_limit_max_requests=2,
            rate_limit_window_seconds=1,  # ventana de 1s
        )
        app = _build_app(settings)
        client = TestClient(app)

        # Primeros 2 requests → 200
        resp1 = client.get("/test")
        assert resp1.status_code == 200
        resp2 = client.get("/test")
        assert resp2.status_code == 200

        # 3ro → 429
        resp3 = client.get("/test")
        assert resp3.status_code == 429

        # Esperamos que pase la ventana
        time.sleep(1.1)

        # Ahora debería aceptar de nuevo
        resp4 = client.get("/test")
        assert resp4.status_code == 200, f"Esperado 200 después de la ventana, obtuvo {resp4.status_code}"

    def test_rate_limit_disabled(self) -> None:
        """Con rate_limit_enabled=false no bloquea nunca."""
        settings = Settings(
            rate_limit_enabled=False,
            rate_limit_max_requests=3,
            rate_limit_window_seconds=60,
        )
        app = _build_app(settings)
        client = TestClient(app)

        # 10 requests rápidos — todos deben ser 200
        for i in range(10):
            resp = client.get("/test")
            assert resp.status_code == 200, f"Request {i+1}: esperado 200, obtuvo {resp.status_code}"

