"""CORS de la API para la consola web (Semana 5, módulo Jorge).

Verifica que solo el origen de la consola recibe cabeceras CORS y que un origen
no autorizado no obtiene `access-control-allow-origin`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.infrastructure.config.settings import settings
from app.main import create_app

_ALLOWED = settings.cors_allowed_origins_list[0]  # http://localhost:3000 por defecto


def test_allowed_origin_gets_cors_header() -> None:
    client = TestClient(create_app())

    resp = client.get("/", headers={"Origin": _ALLOWED})

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == _ALLOWED


def test_disallowed_origin_gets_no_cors_header() -> None:
    client = TestClient(create_app())

    resp = client.get("/", headers={"Origin": "http://evil.example"})

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") is None


def test_preflight_allows_api_key_header() -> None:
    client = TestClient(create_app())

    resp = client.options(
        "/cases",
        headers={
            "Origin": _ALLOWED,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == _ALLOWED
    allow_headers = resp.headers.get("access-control-allow-headers", "").lower()
    assert "x-api-key" in allow_headers
