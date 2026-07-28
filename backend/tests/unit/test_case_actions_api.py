"""Acciones sobre casos: assign / resolve (Semana 5, módulo Jorge).

Verifica que asignar y resolver cambian el estado del caso y añaden auditoría sin
alterar la previa (append-only), que devuelven 404 si el caso no existe, 422 si
falta la resolución, y que exigen rol Analista/Administrador (401/403).
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.application.use_cases.assign_case import coerce_uuid
from app.domain.entities.explanation import Explanation
from app.domain.repositories.case_read_repository import CaseDetail
from app.domain.value_objects.role import Role
from app.infrastructure.repositories.in_memory_case_read_repository import (
    InMemoryCaseReadRepository,
)
from app.infrastructure.repositories.in_memory_case_write_repository import (
    InMemoryCaseWriteRepository,
)
from app.main import create_app
from app.presentation.api.dependencies.cases import (
    get_case_read_repository,
    get_case_write_repository,
)
from app.presentation.api.dependencies.security import AuthPolicy, get_auth_policy

_OPENED = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
_INITIAL_AUDIT = {"accion": "INSERT", "usuario": "svc", "fecha": _OPENED.isoformat()}


def _detail(case_id: str = "c1") -> CaseDetail:
    explanation = Explanation(
        transaction_id=uuid4(),
        account_id="acc-001",
        score=55,
        threshold=50,
        is_case=True,
        summary="Caso de prueba",
        reasons=[],
        generated_at=_OPENED,
    )
    return CaseDetail(
        case_id=case_id,
        transaction_id=str(uuid4()),
        account_id="acc-001",
        status="Abierto",
        opened_at=_OPENED,
        explanation=explanation,
        audit_trail=[dict(_INITIAL_AUDIT)],
    )


def _client(cases: list[CaseDetail], keys: dict[str, Role] | None = None):
    app = create_app()
    read = InMemoryCaseReadRepository(cases)
    write = InMemoryCaseWriteRepository(read_repository=read)
    app.dependency_overrides[get_case_read_repository] = lambda: read
    app.dependency_overrides[get_case_write_repository] = lambda: write
    if keys is not None:
        app.dependency_overrides[get_auth_policy] = lambda: AuthPolicy(
            enabled=True, keys=keys
        )
    return TestClient(app), read


# --------------------------- assign ----------------------------------------

def test_assign_changes_status_and_appends_audit() -> None:
    client, read = _client([_detail()])
    assignee = "550e8400-e29b-41d4-a716-446655440000"

    resp = client.post("/cases/c1/assign", json={"assigneeId": assignee})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "En Investigacion"
    assert body["assignedTo"] == assignee
    # La auditoría creció y la entrada previa NO se alteró (append-only).
    audit = read.get_case("c1").audit_trail
    assert len(audit) == 2
    assert audit[0] == _INITIAL_AUDIT


def test_assign_to_me_derives_assignee() -> None:
    client, _ = _client([_detail()])

    resp = client.post("/cases/c1/assign", json={})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "En Investigacion"
    assert body["assignedTo"]  # se derivó un id estable


def test_assign_404_when_missing() -> None:
    client, _ = _client([_detail()])

    resp = client.post("/cases/nope/assign", json={})

    assert resp.status_code == 404
    assert resp.json()["code"] == "CASE_NOT_FOUND"


# --------------------------- resolve ---------------------------------------

def test_resolve_changes_status_and_appends_audit() -> None:
    client, read = _client([_detail()])

    resp = client.post(
        "/cases/c1/resolve",
        json={"resolution": "Fraude confirmado", "note": "cuenta bloqueada"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "Resuelto"
    audit = read.get_case("c1").audit_trail
    assert len(audit) == 2
    assert audit[0] == _INITIAL_AUDIT
    assert "Fraude confirmado" in audit[1]["detalle"]


def test_resolve_404_when_missing() -> None:
    client, _ = _client([_detail()])

    resp = client.post("/cases/nope/resolve", json={"resolution": "x"})

    assert resp.status_code == 404


def test_resolve_requires_resolution() -> None:
    client, _ = _client([_detail()])

    empty = client.post("/cases/c1/resolve", json={"resolution": ""})
    missing = client.post("/cases/c1/resolve", json={})

    assert empty.status_code == 422
    assert missing.status_code == 422


# --------------------------- roles -----------------------------------------

def test_assign_requires_api_key() -> None:
    client, _ = _client([_detail()], keys={"ana-key": Role.ANALISTA})

    resp = client.post("/cases/c1/assign", json={})

    assert resp.status_code == 401


def test_assign_forbidden_for_service_role() -> None:
    client, _ = _client([_detail()], keys={"svc-key": Role.SERVICIO})

    resp = client.post(
        "/cases/c1/assign", json={}, headers={"X-API-Key": "svc-key"}
    )

    assert resp.status_code == 403


def test_assign_forbidden_for_auditor() -> None:
    client, _ = _client([_detail()], keys={"aud-key": Role.AUDITOR})

    resp = client.post(
        "/cases/c1/assign", json={}, headers={"X-API-Key": "aud-key"}
    )

    assert resp.status_code == 403


def test_resolve_allowed_for_analyst() -> None:
    client, _ = _client([_detail()], keys={"ana-key": Role.ANALISTA})

    resp = client.post(
        "/cases/c1/resolve",
        json={"resolution": "ok"},
        headers={"X-API-Key": "ana-key"},
    )

    assert resp.status_code == 200


# --------------------------- coerce_uuid -----------------------------------

def test_coerce_uuid_passes_through_valid_uuid() -> None:
    value = "550e8400-e29b-41d4-a716-446655440000"
    assert coerce_uuid(value) == value


def test_coerce_uuid_derives_stable_uuid_from_plain_string() -> None:
    first = coerce_uuid("analista")
    second = coerce_uuid("analista")
    assert first == second
    UUID(first)  # es un UUID válido
