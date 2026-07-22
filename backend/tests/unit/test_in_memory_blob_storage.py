from __future__ import annotations

from app.infrastructure.repositories.in_memory_blob_storage import (
    InMemoryBlobStorage,
)


def test_upload_then_exists_and_download_round_trip() -> None:
    storage = InMemoryBlobStorage()
    data = b"%PDF-1.4 comprobante"

    returned_name = storage.upload("doc-1.pdf", data, "application/pdf")

    assert returned_name == "doc-1.pdf"
    assert storage.exists("doc-1.pdf")
    assert storage.download("doc-1.pdf") == data


def test_exists_is_false_for_unknown_blob() -> None:
    storage = InMemoryBlobStorage()

    assert storage.exists("missing.pdf") is False


def test_upload_overwrites_existing_blob() -> None:
    storage = InMemoryBlobStorage()

    storage.upload("doc.pdf", b"v1", "application/pdf")
    storage.upload("doc.pdf", b"v2", "application/pdf")

    assert storage.download("doc.pdf") == b"v2"
