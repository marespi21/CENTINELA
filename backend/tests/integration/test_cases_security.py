"""Seguridad de la API de revisión de casos (Semana 3, módulo Lucas).

Verifica que GET /cases/{caseId} y el acceso a documentos exigen rol de lectura
(Analista/Auditor/Administrador): 401 sin clave, 403 con rol no autorizado, 200
con rol válido; y que el documento se sirve por una URL temporal (SAS).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from app.application.services.rule_based_explainer import RuleBasedExplainer
from app.domain.entities.rule_result import RuleResult
from app.domain.entities.scoring_result import ScoringResult
from app.domain.repositories.case_read_repository import CaseDetail
from app.domain.services.rules import RULE_VELOCITY
from app.domain.value_objects.role import Role
from app.infrastructure.repositories.in_memory_case_read_repository import (
    InMemoryCaseReadRepository,
)
from app.main import create_app
from app.presentation.api.dependencies.cases import get_case_read_repository
from app.presentation.api.dependencies.security import AuthPolicy, get_auth_policy

_CASE_ID = "case-1"
_TX = UUID("550e8400-e29b-41d4-a716-446655440000")


def _detail() -> CaseDetail:
    result = ScoringResult(
        transaction_id=_TX, account_id="acc-001", score=55, threshold=50,
        rule_results=[RuleResult(RULE_VELOCITY, True, 25, {"count_in_window": 6})],
        is_case=True, scored_at=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
    )
    return CaseDetail(
        case_id=_CASE_ID, transaction_id=str(_TX), account_id="acc-001",
        status="Abierto", opened_at=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
        explanation=RuleBasedExplainer().explain(result), audit_trail=[],
    )


def _client(keys: dict[str, Role], with_case: bool = True) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_auth_policy] = lambda: AuthPolicy(enabled=True, keys=keys)
    repo = InMemoryCaseReadRepository([_detail()] if with_case else [])
    app.dependency_overrides[get_case_read_repository] = lambda: repo
    return TestClient(app)


def test_get_case_requires_api_key() -> None:
    client = _client({"ana-key": Role.ANALISTA})
    resp = client.get(f"/cases/{_CASE_ID}")
    assert resp.status_code == 401
    assert resp.json()["code"] == "UNAUTHORIZED"


def test_get_case_forbidden_for_service_role() -> None:
    client = _client({"svc-key": Role.SERVICIO})
    resp = client.get(f"/cases/{_CASE_ID}", headers={"X-API-Key": "svc-key"})
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


def test_get_case_allowed_for_analyst() -> None:
    client = _client({"ana-key": Role.ANALISTA})
    resp = client.get(f"/cases/{_CASE_ID}", headers={"X-API-Key": "ana-key"})
    assert resp.status_code == 200
    assert resp.json()["caseId"] == _CASE_ID


def test_get_case_allowed_for_auditor() -> None:
    client = _client({"aud-key": Role.AUDITOR})
    resp = client.get(f"/cases/{_CASE_ID}", headers={"X-API-Key": "aud-key"})
    assert resp.status_code == 200


def test_document_access_requires_auth() -> None:
    client = _client({"ana-key": Role.ANALISTA})
    resp = client.get(f"/cases/{_CASE_ID}/documents/id-doc.pdf")
    assert resp.status_code == 401


def test_document_access_returns_temporary_url() -> None:
    client = _client({"ana-key": Role.ANALISTA})
    resp = client.get(
        f"/cases/{_CASE_ID}/documents/id-doc.pdf",
        headers={"X-API-Key": "ana-key"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "id-doc.pdf" in body["url"]
    assert "expiresAt" in body  # es temporal
