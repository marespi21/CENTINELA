"""Tests de las sondas de salud del contenedor (Sprint 6, Fase 1)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


class TestHealthEndpoints:
    def test_liveness_responde_ok(self) -> None:
        client = TestClient(create_app())
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_readiness_declara_los_adaptadores(self) -> None:
        """Distingue un contenedor conectado a Azure de uno caído a memoria."""
        client = TestClient(create_app())
        response = client.get("/health/ready")

        assert response.status_code == 200
        adapters = response.json()["adapters"]
        assert set(adapters) == {"cosmos", "casesDb", "queue"}

    def test_las_sondas_no_consumen_el_rate_limit(self) -> None:
        """Regresión: con el límite por defecto (10/min) las probes daban 429.

        Container Apps sondea /health cada pocos segundos desde la misma IP; si
        contara para el rate limit, la probe fallaría y la plataforma reiniciaría
        en bucle un contenedor perfectamente sano.
        """
        client = TestClient(create_app())

        codigos = {client.get("/health").status_code for _ in range(30)}

        assert codigos == {200}

    def test_las_rutas_normales_siguen_limitadas(self) -> None:
        """La exención es solo para las sondas: el resto conserva su protección."""
        client = TestClient(create_app())

        codigos = [client.get("/").status_code for _ in range(30)]

        assert 429 in codigos
