"""Rate limiting por origen real detrás de proxy (Semana 3, hardening Lucas).

Detrás de App Service/Front Door la IP del cliente viaja en `X-Forwarded-For`.
El limitador debe contar por ese origen real, no por el peer del proxy.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.infrastructure.config.settings import Settings
from app.presentation.api.middlewares.rate_limit import RateLimitMiddleware


def _client() -> TestClient:
    settings = Settings(
        rate_limit_enabled=True,
        rate_limit_max_requests=1,
        rate_limit_window_seconds=60,
    )
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, settings=settings)

    @app.get("/t")
    def _t() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_counts_per_forwarded_origin() -> None:
    client = _client()
    # Dos clientes reales distintos (mismo proxy) -> buckets separados.
    assert client.get("/t", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 200
    assert client.get("/t", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 200
    # El mismo cliente supera el límite.
    assert client.get("/t", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429


def test_uses_first_ip_of_the_chain() -> None:
    client = _client()
    # Cadena cliente, proxy1: se toma el primero (el cliente real).
    assert client.get("/t", headers={"X-Forwarded-For": "9.9.9.9, 10.0.0.1"}).status_code == 200
    assert client.get("/t", headers={"X-Forwarded-For": "9.9.9.9, 10.0.0.2"}).status_code == 429
