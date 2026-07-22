from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.domain.value_objects.role import Role
from app.main import app
from app.presentation.api.dependencies.security import AuthPolicy, get_auth_policy

client = TestClient(app)


def _enable_auth(keys: dict[str, Role]) -> None:
    app.dependency_overrides[get_auth_policy] = lambda: AuthPolicy(
        enabled=True, keys=keys
    )


def teardown_function() -> None:
    app.dependency_overrides.clear()


def _pdf() -> dict:
    return {"file": ("r.pdf", b"%PDF-1.4 x", "application/pdf")}


def test_document_missing_api_key_returns_401() -> None:
    _enable_auth({"svc-key": Role.SERVICIO})
    response = client.post("/documents", files=_pdf())
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_document_wrong_role_returns_403() -> None:
    _enable_auth({"aud-key": Role.AUDITOR})
    response = client.post(
        "/documents", files=_pdf(), headers={"X-API-Key": "aud-key"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_document_valid_service_role_returns_202() -> None:
    _enable_auth({"svc-key": Role.SERVICIO})
    response = client.post(
        "/documents", files=_pdf(), headers={"X-API-Key": "svc-key"}
    )
    assert response.status_code == 202


def test_transaction_requires_auth_when_enabled() -> None:
    _enable_auth({"adm-key": Role.ADMINISTRADOR})
    payload = {
        "transactionId": str(uuid4()),
        "accountId": "a1",
        "amount": "100.00",
        "currency": "COP",
        "merchantId": "m1",
        "merchantCategory": "retail",
        "latitude": "4.7",
        "longitude": "-74.0",
    }

    assert client.post("/transactions", json=payload).status_code == 401

    ok = client.post(
        "/transactions", json=payload, headers={"X-API-Key": "adm-key"}
    )
    assert ok.status_code == 202


def test_auth_disabled_by_default_allows_without_key() -> None:
    # Sin override: usa settings reales (AUTH_ENABLED=false por defecto).
    response = client.post("/documents", files=_pdf())
    assert response.status_code == 202
