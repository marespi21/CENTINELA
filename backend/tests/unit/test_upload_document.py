from __future__ import annotations

import json
from uuid import UUID

import pytest

from app.application.dtos.document_dto import UploadDocumentInput
from app.application.use_cases.upload_document import UploadDocumentUseCase
from app.domain.exceptions.document_exceptions import (
    DocumentTooLargeError,
    EmptyDocumentError,
    InvalidDocumentTypeError,
)
from app.infrastructure.messaging.in_memory_queue import InMemoryQueue
from app.infrastructure.repositories.in_memory_blob_storage import (
    InMemoryBlobStorage,
)

ALLOWED = frozenset({"application/pdf", "image/png"})
MAX_BYTES = 1024


def _make_use_case(max_bytes: int = MAX_BYTES):
    blob = InMemoryBlobStorage()
    queue = InMemoryQueue()
    use_case = UploadDocumentUseCase(blob, queue, ALLOWED, max_bytes)
    return use_case, blob, queue


def test_upload_stores_blob_and_enqueues_event() -> None:
    use_case, blob, queue = _make_use_case()

    result = use_case.execute(
        UploadDocumentInput(
            filename="recibo.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4 contenido",
        )
    )

    assert isinstance(result.document_id, UUID)
    assert result.blob_name.endswith(".pdf")
    assert result.status == "accepted"
    assert blob.exists(result.blob_name)

    messages = queue.receive_messages(max_messages=10)
    assert len(messages) == 1
    body = json.loads(messages[0].content)
    assert body["event"] == "document.uploaded"
    assert body["documentId"] == str(result.document_id)
    assert body["blobName"] == result.blob_name


def test_generated_name_preserves_extension_and_is_unique() -> None:
    use_case, _, _ = _make_use_case()

    first = use_case.execute(
        UploadDocumentInput("a.PDF", "application/pdf", b"x")
    )
    second = use_case.execute(
        UploadDocumentInput("b.pdf", "application/pdf", b"y")
    )

    assert first.blob_name.endswith(".pdf")
    assert second.blob_name.endswith(".pdf")
    assert first.blob_name != second.blob_name


def test_rejects_unsupported_type() -> None:
    use_case, blob, queue = _make_use_case()

    with pytest.raises(InvalidDocumentTypeError):
        use_case.execute(
            UploadDocumentInput(
                "virus.exe", "application/x-msdownload", b"data"
            )
        )

    # No debe subir a blob ni encolar si la validación falla.
    assert queue.receive_messages(max_messages=10) == []


def test_rejects_empty_document() -> None:
    use_case, _, _ = _make_use_case()

    with pytest.raises(EmptyDocumentError):
        use_case.execute(
            UploadDocumentInput("empty.pdf", "application/pdf", b"")
        )


def test_rejects_too_large_document() -> None:
    use_case, _, _ = _make_use_case(max_bytes=4)

    with pytest.raises(DocumentTooLargeError):
        use_case.execute(
            UploadDocumentInput("big.pdf", "application/pdf", b"12345")
        )


# --- Vinculación con el caso (Sprint 6, Fase 2) ------------------------------


def test_el_evento_lleva_el_caso_cuando_se_indica() -> None:
    """Contrato productor↔consumidor: sin `caseId` en el mensaje, el worker no
    tiene contra qué contrastar el comprobante y la verificación no ocurre."""
    use_case, _, queue = _make_use_case()

    use_case.execute(
        UploadDocumentInput(
            filename="recibo.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4 contenido",
            case_id="11111111-1111-1111-1111-111111111111",
        )
    )

    body = json.loads(queue.receive_messages(max_messages=1)[0].content)
    assert body["caseId"] == "11111111-1111-1111-1111-111111111111"


def test_sin_caso_la_clave_no_viaja_en_el_evento() -> None:
    """Se omite en vez de mandarse vacía: el consumidor distingue ausencia de
    cadena vacía y evita gastar cuota de OCR sin nada que verificar."""
    use_case, _, queue = _make_use_case()

    use_case.execute(
        UploadDocumentInput(
            filename="recibo.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4 contenido",
        )
    )

    body = json.loads(queue.receive_messages(max_messages=1)[0].content)
    assert "caseId" not in body


def test_el_evento_se_parsea_de_vuelta_al_dto_del_consumidor() -> None:
    """Ida y vuelta: lo que publica la API es exactamente lo que lee el worker."""
    from app.application.dtos.document_event import document_event_from_message

    use_case, _, queue = _make_use_case()
    result = use_case.execute(
        UploadDocumentInput(
            filename="recibo.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4 contenido",
            case_id="caso-1",
        )
    )

    event = document_event_from_message(
        queue.receive_messages(max_messages=1)[0].content
    )

    assert event.blob_name == result.blob_name
    assert event.case_id == "caso-1"
    assert event.content_type == "application/pdf"
