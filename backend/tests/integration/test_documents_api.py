from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_post_document_returns_202() -> None:
    response = client.post(
        "/documents",
        files={"file": ("recibo.pdf", b"%PDF-1.4 contenido", "application/pdf")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "accepted"
    assert body["blobName"].endswith(".pdf")
    assert "documentId" in body


def test_post_document_rejects_unsupported_type() -> None:
    response = client.post(
        "/documents",
        files={"file": ("malware.exe", b"MZ binario", "application/x-msdownload")},
    )

    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_DOCUMENT_TYPE"


def test_post_document_rejects_empty_file() -> None:
    response = client.post(
        "/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "EMPTY_DOCUMENT"
