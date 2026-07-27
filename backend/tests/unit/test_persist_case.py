"""Consumidor de la cola `cases` (Semana 3, módulo Camila).

Verifica: (1) el mensaje incluye la explicación y se parsea al contrato;
(2) el consumidor entrega el caso a gestión de casos (loop escritura -> lectura);
(3) garantía de entrega: consumidor caído/reactivado, cero pérdida, explicación
intacta.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.application.dtos.case_message_dto import opened_case_from_message
from app.application.services.rule_based_explainer import RuleBasedExplainer
from app.application.use_cases.persist_opened_case import PersistOpenedCaseUseCase
from app.domain.entities.rule_result import RuleResult
from app.domain.entities.scoring_result import ScoringResult
from app.domain.services.rules import RULE_ATYPICAL_AMOUNT, RULE_VELOCITY
from app.infrastructure.azure.case_queue import _serialize_case
from app.infrastructure.messaging.in_memory_case_queue import InMemoryCaseQueue
from app.infrastructure.repositories.in_memory_case_read_repository import (
    InMemoryCaseReadRepository,
)
from app.infrastructure.repositories.in_memory_case_write_repository import (
    InMemoryCaseWriteRepository,
)

_TX = UUID("550e8400-e29b-41d4-a716-446655440000")


def _result() -> ScoringResult:
    return ScoringResult(
        transaction_id=_TX, account_id="acc-001", score=55, threshold=50,
        rule_results=[
            RuleResult(RULE_VELOCITY, True, 25, {"count_in_window": 6}),
            RuleResult(RULE_ATYPICAL_AMOUNT, True, 30, {"amount": 900000.0}),
        ],
        is_case=True, scored_at=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
    )


def _message() -> str:
    result = _result()
    explanation = RuleBasedExplainer().explain(result)
    return _serialize_case(result, explanation)  # contrato real de la cola


def test_message_includes_explanation_and_parses() -> None:
    opened = opened_case_from_message(_message())
    assert opened.transaction_id == str(_TX)
    assert opened.account_id == "acc-001"
    assert opened.score == 55
    assert opened.explanation.is_case is True
    assert len(opened.explanation.reasons) == 2


def test_message_without_explanation_is_rejected() -> None:
    result = _result()
    with pytest.raises(ValueError):
        opened_case_from_message(_serialize_case(result))  # sin explicación


def test_consumer_delivers_case_to_case_store() -> None:
    # El consumidor persiste; la API de lectura lo recupera (loop punta a punta).
    read = InMemoryCaseReadRepository()
    write = InMemoryCaseWriteRepository(read_repository=read)
    use_case = PersistOpenedCaseUseCase(write)

    case_id = use_case.execute(_message())

    detail = read.get_case(case_id)
    assert detail is not None
    assert detail.transaction_id == str(_TX)
    assert detail.status == "Abierto"
    assert detail.explanation.is_case is True
    assert len(detail.explanation.reasons) == 2


def test_case_with_explanation_survives_consumer_down_and_restart() -> None:
    cases = InMemoryCaseQueue()
    result = _result()
    explanation = RuleBasedExplainer().explain(result)

    cases.stop_consumer()
    cases.publish_case(result, explanation)

    # Consumidor caído: nada consumido, el caso queda retenido (cero pérdida).
    assert cases.consumed == []
    assert len(cases.pending) == 1

    cases.start_consumer()

    # Reactivado: se procesa el caso, con su explicación intacta.
    assert len(cases.consumed) == 1
    assert cases.explanations[_TX].is_case is True
