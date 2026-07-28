"""Listado de documentos de un caso GET /cases/{id}/documents (Semana 5).

Verifica que se listan los documentos del caso con una URL temporal (SAS) por
cada uno, que un caso sin documentos devuelve lista vacía, y que exige rol de
lectura (401/403). El acceso al contenido nunca es directo: siempre por SAS.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.repositories.case_document_repository import CaseDocument
from app.domain.value_objects.role import Role
from app.infrastructure.postgres.pg_case_document_repository import build_case_document
from app.infrastructure.repositories.in_memory_case_document_repository import (
    InMemoryCaseDocumentRepository,
)
from app.main import create_app
from app.presentation.api.dependencies.cases import get_case_document_repository
from app.presentation.api.dependencies.security import AuthPolicy, get_auth_policy

_NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


def _repo() -> InMemoryCaseDocumentRepository:
    return InMemoryCaseDocumentRepository(
        {
            "c1": [
                CaseDocument("doc-old.pdf", "old.pdf", "application/pdf", _NOW),
                CaseDocument(
                    "doc-new.png", "new.png", "image/png", _NOW + timedelta(hours=1)
                ),
            ]
        }
    )


def _client(keys: dict[str, Role] | None = None) -> TestClient:
    app = create_app()
    repo = _repo()
    app.dependency_overrides[get_case_document_repository] = lambda: repo
    if keys is not None:
        app.dependency_overrides[get_auth_policy] = lambda: AuthPolicy(
            enabled=True, keys=keys
        )
    return TestClient(app)


def test_list_documents_returns_sas_urls_recent_first() -> None:
    client = _client()

    resp = client.get("/cases/c1/documents")

    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [d["blobName"] for d in items] == ["doc-new.png", "doc-old.pdf"]
    first = items[0]
    assert first["filename"] == "new.png"
    assert first["contentType"] == "image/png"
    assert "doc-new.png" in first["url"]  # URL temporal (SAS), no acceso directo
    assert "expiresAt" in first


def test_list_documents_empty_when_case_has_none() -> None:
    client = _client()

    resp = client.get("/cases/sin-docs/documents")

    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_list_documents_requires_api_key() -> None:
    client = _client(keys={"ana-key": Role.ANALISTA})

    resp = client.get("/cases/c1/documents")

    assert resp.status_code == 401


def test_list_documents_forbidden_for_service_role() -> None:
    client = _client(keys={"svc-key": Role.SERVICIO})

    resp = client.get("/cases/c1/documents", headers={"X-API-Key": "svc-key"})

    assert resp.status_code == 403


def test_build_case_document_maps_row() -> None:
    doc = build_case_document(("b.pdf", "factura.pdf", "application/pdf", _NOW))

    assert doc.blob_name == "b.pdf"
    assert doc.filename == "factura.pdf"
    assert doc.content_type == "application/pdf"
    assert doc.uploaded_at == _NOW
