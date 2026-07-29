"""Tests del caso de uso de verificación documental (Sprint 6, Fase 2).

Cubre la cadena blob → OCR → contraste → persistencia con dobles en memoria, y
sobre todo la parte que decide si un mensaje de cola se reintenta o no: un
documento ilegible es un RESULTADO (no reintentar), un OCR caído es un FALLO
(reintentar).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.application.use_cases.verify_document import VerifyDocumentUseCase
from app.domain.entities.document_analysis import DocumentAnalysis
from app.domain.entities.document_verification import VerificationVerdict
from app.domain.entities.explanation import Explanation
from app.domain.entities.transaction import Transaction
from app.domain.repositories.case_read_repository import CaseDetail
from app.domain.repositories.document_analyzer import (
    DocumentAnalysisError,
    DocumentAnalyzer,
)
from app.domain.services.document_verifier import DocumentVerifier
from app.infrastructure.repositories.in_memory_blob_storage import InMemoryBlobStorage
from app.infrastructure.repositories.in_memory_case_document_repository import (
    InMemoryCaseDocumentRepository,
)
from app.infrastructure.repositories.in_memory_case_document_write_repository import (
    InMemoryCaseDocumentWriteRepository,
)
from app.infrastructure.repositories.in_memory_transaction_history_repository import (
    InMemoryTransactionHistoryRepository,
)

TX_ID = uuid4()
TX_TIME = datetime(2026, 7, 20, 15, 30, tzinfo=timezone.utc)
CASE_ID = "11111111-1111-1111-1111-111111111111"
BLOB = "doc-1.pdf"


class FakeAnalyzer(DocumentAnalyzer):
    def __init__(self, analysis: DocumentAnalysis | None = None, error: Exception | None = None):
        self._analysis = analysis or DocumentAnalysis()
        self._error = error
        self.calls = 0

    def analyze(self, content: bytes, content_type: str) -> DocumentAnalysis:
        self.calls += 1
        if self._error:
            raise self._error
        return self._analysis


class FakeCaseReader:
    """Doble del puerto de lectura de casos, con solo lo que usa el caso de uso."""

    def __init__(self, detail: CaseDetail | None) -> None:
        self._detail = detail

    def get_case(self, case_id: str) -> CaseDetail | None:
        return self._detail

    def list_cases(self, query: object) -> object:  # pragma: no cover - no se usa
        raise NotImplementedError


def _case_detail() -> CaseDetail:
    return CaseDetail(
        case_id=CASE_ID,
        transaction_id=str(TX_ID),
        account_id="acc-1",
        status="Abierto",
        opened_at=TX_TIME,
        explanation=Explanation(
            transaction_id=TX_ID,
            account_id="acc-1",
            score=50,
            threshold=50,
            is_case=True,
            generated_at=TX_TIME,
            summary="Caso abierto por importe atípico.",
            reasons=[],
        ),
    )


def _transaction(amount: str = "250000") -> Transaction:
    return Transaction(
        transaction_id=TX_ID,
        account_id="acc-1",
        amount=Decimal(amount),
        currency="COP",
        merchant_id="m1",
        merchant_category="retail",
        timestamp=TX_TIME,
        latitude=Decimal("4.7110"),
        longitude=Decimal("-74.0721"),
    )


def _message(case_id: str | None = CASE_ID, blob: str = BLOB) -> str:
    payload: dict[str, object] = {
        "event": "document.uploaded",
        "documentId": str(uuid4()),
        "blobName": blob,
        "filename": "comprobante.pdf",
        "contentType": "application/pdf",
        "sizeBytes": 1024,
        "uploadedAt": TX_TIME.isoformat(),
    }
    if case_id:
        payload["caseId"] = case_id
    return json.dumps(payload)


# Centinela: hay que distinguir "no me pasaron caso" (usa el de por defecto) de
# "el caso NO existe" (None), y ambos no pueden ser el mismo valor.
_SIN_ESPECIFICAR = object()


def _build(
    analyzer: DocumentAnalyzer,
    detail: CaseDetail | None | object = _SIN_ESPECIFICAR,
    transactions: list[Transaction] | None = None,
) -> tuple[VerifyDocumentUseCase, InMemoryCaseDocumentRepository]:
    blobs = InMemoryBlobStorage()
    blobs.upload(BLOB, b"contenido-del-pdf", "application/pdf")

    history = InMemoryTransactionHistoryRepository()
    for tx in transactions if transactions is not None else [_transaction()]:
        history.add(tx)

    read_docs = InMemoryCaseDocumentRepository()
    writer = InMemoryCaseDocumentWriteRepository(read_docs)

    use_case = VerifyDocumentUseCase(
        blob_storage=blobs,
        analyzer=analyzer,
        verifier=DocumentVerifier(),
        cases=FakeCaseReader(  # type: ignore[arg-type]
            _case_detail() if detail is _SIN_ESPECIFICAR else detail  # type: ignore[arg-type]
        ),
        history=history,
        documents=writer,
    )
    return use_case, read_docs


class TestFlujoCompleto:
    def test_comprobante_coincidente_queda_verificado_en_el_caso(self) -> None:
        analyzer = FakeAnalyzer(
            DocumentAnalysis(
                total=Decimal("250000"), total_confidence=0.95,
                transaction_date=TX_TIME, date_confidence=0.95,
            )
        )
        use_case, docs = _build(analyzer)

        result = use_case.execute(_message())

        assert result is not None
        assert result.verdict is VerificationVerdict.COINCIDE
        guardados = docs.list_for_case(CASE_ID)
        assert len(guardados) == 1
        assert guardados[0].verdict == "coincide"
        assert guardados[0].verified_at is not None

    def test_comprobante_que_discrepa_queda_marcado(self) -> None:
        analyzer = FakeAnalyzer(
            DocumentAnalysis(total=Decimal("10"), total_confidence=0.95)
        )
        use_case, docs = _build(analyzer)

        result = use_case.execute(_message())

        assert result is not None and result.is_suspicious
        assert docs.list_for_case(CASE_ID)[0].verdict == "discrepa"

    def test_reprocesar_el_mismo_mensaje_no_duplica_el_documento(self) -> None:
        """La cola entrega 'al menos una vez': el flujo debe ser idempotente."""
        analyzer = FakeAnalyzer(
            DocumentAnalysis(total=Decimal("250000"), total_confidence=0.95)
        )
        use_case, docs = _build(analyzer)

        use_case.execute(_message())
        use_case.execute(_message())

        assert len(docs.list_for_case(CASE_ID)) == 1


class TestCasosSinContraste:
    def test_documento_sin_caso_no_se_verifica(self) -> None:
        """Subir un documento suelto es válido; simplemente no hay qué contrastar."""
        analyzer = FakeAnalyzer()
        use_case, docs = _build(analyzer)

        result = use_case.execute(_message(case_id=None))

        assert result is None
        assert analyzer.calls == 0, "no debe gastarse cuota de OCR sin caso"
        assert docs.list_for_case(CASE_ID) == []

    def test_caso_inexistente_registra_el_documento_sin_veredicto(self) -> None:
        analyzer = FakeAnalyzer()
        use_case, docs = _build(analyzer, detail=None)

        result = use_case.execute(_message())

        assert result is None
        assert analyzer.calls == 0
        guardados = docs.list_for_case(CASE_ID)
        assert len(guardados) == 1 and guardados[0].verdict is None

    def test_transaccion_ausente_del_historial_registra_sin_veredicto(self) -> None:
        analyzer = FakeAnalyzer()
        use_case, docs = _build(analyzer, transactions=[])

        assert use_case.execute(_message()) is None
        assert docs.list_for_case(CASE_ID)[0].verdict is None


class TestManejoDeErrores:
    def test_documento_ilegible_es_un_resultado_no_un_fallo(self) -> None:
        """No debe reintentarse: gastaría cuota F0 para obtener lo mismo."""
        use_case, docs = _build(FakeAnalyzer(DocumentAnalysis()))

        result = use_case.execute(_message())

        assert result is not None
        assert result.verdict is VerificationVerdict.ILEGIBLE
        assert docs.list_for_case(CASE_ID)[0].verdict == "ilegible"

    def test_ocr_caido_propaga_para_que_el_worker_reintente(self) -> None:
        """El worker solo borra el mensaje si el handler no lanza."""
        use_case, docs = _build(
            FakeAnalyzer(error=DocumentAnalysisError("servicio no disponible"))
        )

        with pytest.raises(DocumentAnalysisError):
            use_case.execute(_message())

        assert docs.list_for_case(CASE_ID) == [], "no se persiste un veredicto a medias"

    def test_mensaje_corrupto_se_rechaza(self) -> None:
        use_case, _ = _build(FakeAnalyzer())

        with pytest.raises(ValueError):
            use_case.execute("{no es json")

    def test_mensaje_sin_blob_name_se_rechaza(self) -> None:
        use_case, _ = _build(FakeAnalyzer())

        with pytest.raises(ValueError, match="blobName"):
            use_case.execute(json.dumps({"event": "document.uploaded"}))
