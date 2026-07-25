"""Integración del explicador en el flujo del worker (Semana 3, módulo Jorge).

Prueba de punta a punta (con adaptadores en memoria): una transacción que supera
el umbral produce un caso con su score persistido y su explicación adjunta y
publicada, conforme al contrato.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.application.use_cases.score_transaction import ScoreTransactionUseCase
from app.domain.entities.transaction import Transaction
from app.domain.services.rules import RULE_ATYPICAL_AMOUNT, RULE_VELOCITY
from app.domain.value_objects.scoring_config import ScoringConfig
from app.infrastructure.azure.case_queue import _serialize_case
from app.infrastructure.messaging.in_memory_case_queue import InMemoryCaseQueue
from app.infrastructure.repositories.in_memory_score_repository import (
    InMemoryScoreRepository,
)
from app.infrastructure.repositories.in_memory_transaction_history_repository import (
    InMemoryTransactionHistoryRepository,
)

_BASE = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
_LAT, _LON = Decimal("4.7110"), Decimal("-74.0721")


def _tx(amount: str, minutes_offset: int, tx_id: UUID | None = None) -> Transaction:
    return Transaction(
        transaction_id=tx_id or uuid4(),
        account_id="acc-001",
        amount=Decimal(amount),
        currency="COP",
        merchant_id="mer-1",
        merchant_category="restaurants",
        timestamp=_BASE + timedelta(minutes=minutes_offset),
        latitude=_LAT,
        longitude=_LON,
    )


def _use_case(cases: InMemoryCaseQueue, priors: list[Transaction]) -> ScoreTransactionUseCase:
    return ScoreTransactionUseCase(
        history_repository=InMemoryTransactionHistoryRepository(transactions=priors),
        score_repository=InMemoryScoreRepository(),
        case_queue=cases,
        config=ScoringConfig(),
    )


def test_case_over_threshold_persists_and_publishes_with_explanation() -> None:
    # 4 transacciones pequenas en la misma ventana -> dispara velocidad;
    # la actual con monto enorme -> dispara monto atipico. 25 + 30 = 55 >= 50.
    priors = [_tx("100", -4), _tx("100", -3), _tx("100", -2), _tx("100", -1)]
    current_id = uuid4()
    current = _tx("900000", 0, tx_id=current_id)

    cases = InMemoryCaseQueue()
    scores = InMemoryScoreRepository()
    use_case = ScoreTransactionUseCase(
        history_repository=InMemoryTransactionHistoryRepository(transactions=priors),
        score_repository=scores,
        case_queue=cases,
        config=ScoringConfig(),
    )

    result = use_case.execute(current)

    # Se abrio caso y se persistio el score.
    assert result.is_case
    assert result.score == 55
    assert scores.get(current_id) is not None

    # Se publico el caso con su explicacion adjunta.
    assert len(cases.published) == 1
    assert current_id in cases.explanations
    explanation = cases.explanations[current_id]
    assert explanation.is_case
    rule_ids = {r.rule_id for r in explanation.reasons}
    assert rule_ids == {RULE_VELOCITY, RULE_ATYPICAL_AMOUNT}
    assert "Caso abierto" in explanation.summary

    # El mensaje serializado a la cola incluye el bloque de explicacion.
    payload = json.loads(_serialize_case(result, explanation))
    assert payload["event"] == "case.opened"
    assert payload["explanation"]["isCase"] is True
    assert len(payload["explanation"]["reasons"]) == 2


def test_below_threshold_does_not_publish_or_explain() -> None:
    current = _tx("100", 0)  # sin historial ni senales -> no abre caso
    cases = InMemoryCaseQueue()
    use_case = _use_case(cases, priors=[])

    result = use_case.execute(current)

    assert not result.is_case
    assert cases.published == []
    assert cases.explanations == {}
