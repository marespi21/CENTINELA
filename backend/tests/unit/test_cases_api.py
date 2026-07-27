"""API de revisión de casos (Semana 3, módulo Juan José).

Verifica GET /cases/{caseId}: 200 con caso + explicación + traza (camelCase),
404 (CASE_NOT_FOUND) si no existe, y el mapeo de filas PostgreSQL -> CaseDetail.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.application.dtos.explanation_dto import serialize_explanation
from app.application.services.rule_based_explainer import RuleBasedExplainer
from app.domain.entities.rule_result import RuleResult
from app.domain.entities.scoring_result import ScoringResult
from app.domain.repositories.case_read_repository import CaseDetail
from app.domain.services.rules import RULE_ATYPICAL_AMOUNT, RULE_VELOCITY
from app.infrastructure.postgres.pg_case_read_repository import build_case_detail
from app.infrastructure.repositories.in_memory_case_read_repository import (
    InMemoryCaseReadRepository,
)
from app.main import create_app
from app.presentation.api.dependencies.cases import get_case_read_repository

_CASE_ID = "11111111-1111-1111-1111-111111111111"
_TX_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
_OPENED = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


def _explanation():
    result = ScoringResult(
        transaction_id=_TX_ID,
        account_id="acc-001",
        score=55,
        threshold=50,
        rule_results=[
            RuleResult(rule_id=RULE_VELOCITY, triggered=True, points=25,
                       observed={"count_in_window": 6, "window_minutes": 10, "limit": 5}),
            RuleResult(rule_id=RULE_ATYPICAL_AMOUNT, triggered=True, points=30,
                       observed={"amount": 900000.0, "limit": 300.0, "basis": "account_average"}),
        ],
        is_case=True,
        scored_at=_OPENED,
    )
    return RuleBasedExplainer().explain(result)


def _case_detail() -> CaseDetail:
    return CaseDetail(
        case_id=_CASE_ID,
        transaction_id=str(_TX_ID),
        account_id="acc-001",
        status="Abierto",
        opened_at=_OPENED,
        explanation=_explanation(),
        audit_trail=[{"accion": "INSERT", "usuario": "svc", "fecha": "2026-07-25T12:00:00Z"}],
    )


def _client(detail: CaseDetail | None) -> TestClient:
    app = create_app()
    repo = InMemoryCaseReadRepository([detail] if detail else [])
    app.dependency_overrides[get_case_read_repository] = lambda: repo
    return TestClient(app)


def test_get_case_returns_detail_with_explanation() -> None:
    client = _client(_case_detail())

    resp = client.get(f"/cases/{_CASE_ID}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["caseId"] == _CASE_ID
    assert body["transactionId"] == str(_TX_ID)
    assert body["accountId"] == "acc-001"
    assert body["status"] == "Abierto"
    assert body["explanation"]["isCase"] is True
    assert len(body["explanation"]["reasons"]) == 2
    assert body["auditTrail"][0]["accion"] == "INSERT"


def test_get_case_404_when_missing() -> None:
    client = _client(None)

    resp = client.get("/cases/does-not-exist")

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "CASE_NOT_FOUND"
    assert body["caseId"] == "does-not-exist"


def test_pg_build_case_detail_maps_rows() -> None:
    explanation_json = serialize_explanation(_explanation())
    case_row = (_CASE_ID, str(_TX_ID), "acc-001", "Abierto", _OPENED)
    audit_rows = [
        {"accion": "INSERT", "usuario_accion": "svc", "fecha_registro": _OPENED},
    ]

    detail = build_case_detail(case_row, explanation_json, audit_rows)

    assert detail.case_id == _CASE_ID
    assert detail.transaction_id == str(_TX_ID)
    assert detail.account_id == "acc-001"
    assert detail.status == "Abierto"
    assert detail.explanation.is_case is True
    assert len(detail.explanation.reasons) == 2
    assert detail.audit_trail[0]["usuario"] == "svc"
    assert "2026-07-25" in detail.audit_trail[0]["fecha"]
