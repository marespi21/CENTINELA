"""Tests del explicador asíncrono (Sprint 6, Fase 4).

La propiedad que sostiene todo el diseño: **el caso nunca depende del
enriquecimiento**. Se abre, se persiste y se ve en la bandeja con su explicación
por reglas, pase lo que pase después. Si esto se rompiera, habríamos metido un
servicio lento y falible en el camino crítico de detección de fraude, que es
justo lo contrario de lo que persigue la fase.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.application.dtos.explanation_request import (
    explanation_request_from_message,
    explanation_request_to_message,
    ExplanationRequested,
)
from app.application.services.null_explanation_enricher import NullExplanationEnricher
from app.application.use_cases.enrich_explanation import EnrichExplanationUseCase
from app.application.use_cases.persist_opened_case import PersistOpenedCaseUseCase
from app.domain.entities.explanation import Explanation
from app.domain.repositories.case_read_repository import CaseDetail
from app.domain.services.explanation_enricher import (
    EnrichmentContext,
    ExplanationEnricher,
    ExplanationEnrichmentError,
)
from app.infrastructure.messaging.in_memory_explanation_queue import (
    InMemoryExplanationQueue,
)
from app.infrastructure.repositories.in_memory_case_explanation_repository import (
    InMemoryCaseExplanationRepository,
)
from app.infrastructure.repositories.in_memory_case_write_repository import (
    InMemoryCaseWriteRepository,
)

TX_ID = uuid4()
CASE_ID = "11111111-1111-1111-1111-111111111111"
NOW = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)


def _explanation(summary: str = "Caso abierto por importe atípico.") -> Explanation:
    return Explanation(
        transaction_id=TX_ID,
        account_id="acc-1",
        score=50,
        threshold=50,
        is_case=True,
        summary=summary,
        reasons=[],
        generated_at=NOW,
    )


def _case_message() -> str:
    return json.dumps(
        {
            "event": "case.opened",
            "transactionId": str(TX_ID),
            "accountId": "acc-1",
            "score": 50,
            "threshold": 50,
            "scoredAt": NOW.isoformat().replace("+00:00", "Z"),
            "triggeredRules": [],
            "explanation": {
                "transactionId": str(TX_ID),
                "accountId": "acc-1",
                "score": 50,
                "threshold": 50,
                "isCase": True,
                "summary": "Caso abierto por importe atípico.",
                "reasons": [],
                "generatedAt": NOW.isoformat().replace("+00:00", "Z"),
            },
        }
    )


class FakeCaseReader:
    def __init__(self, detail: CaseDetail | None) -> None:
        self._detail = detail

    def get_case(self, case_id: str) -> CaseDetail | None:
        return self._detail

    def list_cases(self, query: object) -> object:  # pragma: no cover
        raise NotImplementedError


def _case_detail() -> CaseDetail:
    return CaseDetail(
        case_id=CASE_ID,
        transaction_id=str(TX_ID),
        account_id="acc-1",
        status="Abierto",
        opened_at=NOW,
        explanation=_explanation(),
    )


class TestElCasoNoDependeDelEnriquecimiento:
    def test_persistir_dispara_la_peticion_despues_de_guardar(self) -> None:
        """Se pide DESPUÉS de persistir: el enriquecedor necesita el case_id."""
        queue = InMemoryExplanationQueue()
        use_case = PersistOpenedCaseUseCase(
            InMemoryCaseWriteRepository(), explanation_queue=queue
        )

        case_id = use_case.execute(_case_message())

        assert len(queue.requests) == 1
        assert queue.requests[0].case_id == case_id
        assert queue.requests[0].account_id == "acc-1"

    def test_si_la_cola_de_enriquecimiento_falla_el_caso_sigue_guardado(self) -> None:
        """El fallo NO se propaga.

        Si se propagara, la cola reintentaría el mensaje del caso y acabaríamos
        duplicando casos de fraude: mucho peor que quedarse sin narrativa.
        """

        class ColaRota(InMemoryExplanationQueue):
            def request_enrichment(self, case_id, transaction_id, account_id):  # type: ignore[override]
                raise ConnectionError("storage inalcanzable")

        repo = InMemoryCaseWriteRepository()
        use_case = PersistOpenedCaseUseCase(repo, explanation_queue=ColaRota())

        case_id = use_case.execute(_case_message())

        assert case_id, "el caso debe quedar persistido pese al fallo de la cola"

    def test_sin_cola_configurada_el_flujo_sigue_funcionando(self) -> None:
        """Compatibilidad: el consumidor previo a la Fase 4 no pasaba cola."""
        use_case = PersistOpenedCaseUseCase(InMemoryCaseWriteRepository())

        assert use_case.execute(_case_message())


class TestEnriquecimiento:
    def test_la_version_enriquecida_se_anade_sin_borrar_la_anterior(self) -> None:
        """Append-only: la explicación por reglas queda como traza auditada."""

        class Enriquecedor(ExplanationEnricher):
            def enrich(self, context: EnrichmentContext) -> Explanation | None:
                return _explanation("Narrativa enriquecida del caso.")

        repo = InMemoryCaseExplanationRepository()
        # Se siembra la versión por reglas, como haría save_opened_case.
        repo.append_explanation(CASE_ID, _explanation())

        use_case = EnrichExplanationUseCase(
            cases=FakeCaseReader(_case_detail()),  # type: ignore[arg-type]
            explanations=repo,
            enricher=Enriquecedor(),
        )
        resultado = use_case.execute(
            explanation_request_to_message(
                ExplanationRequested(CASE_ID, str(TX_ID), "acc-1")
            )
        )

        assert resultado is not None
        versiones = repo.versions_for(CASE_ID)
        assert len(versiones) == 2, "la versión anterior no puede desaparecer"
        # La lectura toma la más reciente, igual que el adaptador PostgreSQL.
        assert repo.latest_for(CASE_ID).summary == "Narrativa enriquecida del caso."
        assert versiones[0].summary == "Caso abierto por importe atípico."

    def test_el_enriquecedor_recibe_la_explicacion_base(self) -> None:
        capturado: list[EnrichmentContext] = []

        class Espia(ExplanationEnricher):
            def enrich(self, context: EnrichmentContext) -> Explanation | None:
                capturado.append(context)
                return None

        EnrichExplanationUseCase(
            cases=FakeCaseReader(_case_detail()),  # type: ignore[arg-type]
            explanations=InMemoryCaseExplanationRepository(),
            enricher=Espia(),
        ).execute(
            explanation_request_to_message(
                ExplanationRequested(CASE_ID, str(TX_ID), "acc-1")
            )
        )

        assert len(capturado) == 1
        assert capturado[0].case_id == CASE_ID
        assert capturado[0].base_explanation.summary == "Caso abierto por importe atípico."

    def test_sin_enriquecedor_configurado_no_se_escribe_nada(self) -> None:
        """Adaptador nulo: la tubería funciona antes de elegir el servicio."""
        repo = InMemoryCaseExplanationRepository()

        resultado = EnrichExplanationUseCase(
            cases=FakeCaseReader(_case_detail()),  # type: ignore[arg-type]
            explanations=repo,
            enricher=NullExplanationEnricher(),
        ).execute(
            explanation_request_to_message(
                ExplanationRequested(CASE_ID, str(TX_ID), "acc-1")
            )
        )

        assert resultado is None
        assert repo.versions_for(CASE_ID) == []


class TestManejoDeErrores:
    def test_servicio_caido_propaga_para_reintentar(self) -> None:
        class Roto(ExplanationEnricher):
            def enrich(self, context: EnrichmentContext) -> Explanation | None:
                raise ExplanationEnrichmentError("servicio no disponible")

        with pytest.raises(ExplanationEnrichmentError):
            EnrichExplanationUseCase(
                cases=FakeCaseReader(_case_detail()),  # type: ignore[arg-type]
                explanations=InMemoryCaseExplanationRepository(),
                enricher=Roto(),
            ).execute(
                explanation_request_to_message(
                    ExplanationRequested(CASE_ID, str(TX_ID), "acc-1")
                )
            )

    def test_caso_inexistente_se_descarta_sin_reintentar(self) -> None:
        """Reintentar contra algo que no existe es un bucle infinito."""
        resultado = EnrichExplanationUseCase(
            cases=FakeCaseReader(None),  # type: ignore[arg-type]
            explanations=InMemoryCaseExplanationRepository(),
            enricher=NullExplanationEnricher(),
        ).execute(
            explanation_request_to_message(
                ExplanationRequested(CASE_ID, str(TX_ID), "acc-1")
            )
        )

        assert resultado is None

    def test_mensaje_sin_case_id_se_rechaza(self) -> None:
        with pytest.raises(ValueError, match="caseId"):
            explanation_request_from_message(json.dumps({"event": "x"}))


class TestContratoDeCola:
    def test_ida_y_vuelta_del_mensaje(self) -> None:
        original = ExplanationRequested(CASE_ID, str(TX_ID), "acc-1")

        recuperado = explanation_request_from_message(
            explanation_request_to_message(original)
        )

        assert recuperado == original
