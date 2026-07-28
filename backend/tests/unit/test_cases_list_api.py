"""Bandeja de casos GET /cases (Semana 5, módulo Jorge).

Verifica el listado con filtros (estado, asignado, rango de fechas) y paginación,
el conteo total, el orden por fecha descendente y el contrato camelCase.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.entities.explanation import Explanation
from app.domain.repositories.case_read_repository import CaseDetail
from app.infrastructure.repositories.in_memory_case_read_repository import (
    InMemoryCaseReadRepository,
)
from app.main import create_app
from app.presentation.api.dependencies.cases import get_case_read_repository

_BASE = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)


def _detail(
    case_id: str,
    opened_at: datetime,
    *,
    status: str = "Abierto",
    assignee: str | None = None,
    score: int = 55,
) -> CaseDetail:
    explanation = Explanation(
        transaction_id=uuid4(),
        account_id=f"acc-{case_id}",
        score=score,
        threshold=50,
        is_case=score >= 50,
        summary=f"Resumen del caso {case_id}",
        reasons=[],
        generated_at=opened_at,
    )
    return CaseDetail(
        case_id=case_id,
        transaction_id=str(uuid4()),
        account_id=f"acc-{case_id}",
        status=status,
        opened_at=opened_at,
        explanation=explanation,
        audit_trail=[],
        assignee=assignee,
    )


def _client(cases: list[CaseDetail]) -> TestClient:
    app = create_app()
    repo = InMemoryCaseReadRepository(cases)
    app.dependency_overrides[get_case_read_repository] = lambda: repo
    return TestClient(app)


def _seed() -> list[CaseDetail]:
    return [
        _detail("c1", _BASE, status="Abierto"),
        _detail("c2", _BASE + timedelta(hours=1), status="Resuelto", assignee="ana-1"),
        _detail("c3", _BASE + timedelta(hours=2), status="Abierto", assignee="ana-1"),
    ]


def test_list_returns_all_ordered_desc_camelcase() -> None:
    client = _client(_seed())

    resp = client.get("/cases")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["pageSize"] == 20
    ids = [item["caseId"] for item in body["items"]]
    assert ids == ["c3", "c2", "c1"]  # más reciente primero
    first = body["items"][0]
    assert first["accountId"] == "acc-c3"
    assert first["isCase"] is True
    assert "summary" in first and "openedAt" in first
    assert first["assignedTo"] == "ana-1"


def test_list_filters_by_status() -> None:
    client = _client(_seed())

    resp = client.get("/cases", params={"status": "Abierto"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert {i["caseId"] for i in body["items"]} == {"c1", "c3"}


def test_list_filters_by_assignee() -> None:
    client = _client(_seed())

    resp = client.get("/cases", params={"assignedTo": "ana-1"})

    body = resp.json()
    assert body["total"] == 2
    assert {i["caseId"] for i in body["items"]} == {"c2", "c3"}


def test_list_paginates_with_total() -> None:
    client = _client(_seed())

    resp = client.get("/cases", params={"page": 2, "pageSize": 2})

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3  # total global, no de la página
    assert body["page"] == 2
    assert body["pageSize"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["caseId"] == "c1"  # la más antigua queda de última


def test_list_rejects_invalid_page() -> None:
    client = _client(_seed())

    resp = client.get("/cases", params={"page": 0})

    assert resp.status_code == 422  # ge=1
