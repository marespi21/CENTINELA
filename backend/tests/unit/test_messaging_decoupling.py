"""Pruebas de desacoplamiento mensajería/API (módulo Camila, entregable 10).

Criterios:
- La API responde antes de que termine el scoring (timestamps).
- Con el consumidor de casos detenido, la API sigue aceptando.
- Al reactivar el consumidor, cero casos perdidos.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.application.dtos.scoring_dto import transaction_from_event
from app.application.dtos.transaction_dto import ReceiveTransactionInput
from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.application.use_cases.score_transaction import ScoreTransactionUseCase
from app.domain.entities.transaction import Transaction
from app.domain.value_objects.scoring_config import ScoringConfig
from app.infrastructure.messaging.in_memory_case_queue import InMemoryCaseQueue
from app.infrastructure.messaging.in_memory_transaction_event_publisher import (
    InMemoryTransactionEventPublisher,
)
from app.infrastructure.repositories.in_memory_score_repository import (
    InMemoryScoreRepository,
)
from app.infrastructure.repositories.in_memory_transaction_history_repository import (
    InMemoryTransactionHistoryRepository,
)
from app.infrastructure.repositories.in_memory_transaction_repository import (
    InMemoryTransactionRepository,
)

NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)
BOGOTA = (Decimal("4.7110"), Decimal("-74.0721"))
TOKYO = (Decimal("35.6762"), Decimal("139.6503"))
ACCOUNT = "acc-decouple"

# crypto (20) + geo-imposible (45) = 65 ≥ umbral 50 → abre caso.
CONFIG = ScoringConfig(
    threshold=50,
    weight_geo_impossible=45,
    weight_risky_merchant=20,
    risky_categories=frozenset({"crypto"}),
)


def _input() -> ReceiveTransactionInput:
    return ReceiveTransactionInput(
        transaction_id=uuid4(),
        account_id=ACCOUNT,
        amount=Decimal("100"),
        currency="COP",
        merchant_id="mer-x",
        merchant_category="crypto",
        latitude=TOKYO[0],
        longitude=TOKYO[1],
    )


def _prior_bogota() -> Transaction:
    return Transaction(
        transaction_id=uuid4(),
        account_id=ACCOUNT,
        amount=Decimal("100"),
        currency="COP",
        merchant_id="mer-0",
        merchant_category="restaurants",
        timestamp=NOW - timedelta(minutes=10),
        latitude=BOGOTA[0],
        longitude=BOGOTA[1],
    )


def _scoring(cases: InMemoryCaseQueue) -> ScoreTransactionUseCase:
    return ScoreTransactionUseCase(
        history_repository=InMemoryTransactionHistoryRepository([_prior_bogota()]),
        score_repository=InMemoryScoreRepository(),
        case_queue=cases,
        config=CONFIG,
    )


def _force_event_timestamp(event_json: str) -> str:
    """Alinea el timestamp del evento con NOW para que el historial aplique."""
    body = json.loads(event_json)
    body["timestamp"] = NOW.isoformat().replace("+00:00", "Z")
    body["latitude"] = str(TOKYO[0])
    body["longitude"] = str(TOKYO[1])
    body["merchantCategory"] = "crypto"
    body["accountId"] = ACCOUNT
    return json.dumps(body)


def test_api_responds_before_scoring_finishes_timestamps() -> None:
    """La API publica y responde; el scoring corre después (marcas de tiempo)."""
    repository = InMemoryTransactionRepository()
    events = InMemoryTransactionEventPublisher()
    # Consumidor de eventos detenido: el scoring NO corre en el publish.
    events.stop_consumer()
    receive = ReceiveTransactionUseCase(repository, events)

    api_started = datetime.now(timezone.utc)
    result = receive.execute(_input())
    api_responded_at = datetime.now(timezone.utc)

    assert result.status == "accepted"
    assert len(events.published) == 1
    assert events.pending  # scoring aún no consumió

    published_at = datetime.fromisoformat(
        json.loads(events.published[0])["publishedAt"].replace("Z", "+00:00")
    )
    assert api_started <= published_at <= api_responded_at

    # Simular scoring lento DESPUÉS de la respuesta de la API.
    time.sleep(0.05)
    cases = InMemoryCaseQueue()
    scoring_started = datetime.now(timezone.utc)
    scored = _scoring(cases).execute(
        transaction_from_event(_force_event_timestamp(events.published[0]))
    )
    scoring_finished = datetime.now(timezone.utc)

    assert api_responded_at < scoring_started
    assert scoring_started < scoring_finished
    assert scored.is_case is True
    assert api_responded_at < scoring_finished


def test_api_keeps_accepting_when_case_consumer_is_stopped() -> None:
    """Con el consumidor de casos detenido, la API sigue respondiendo."""
    repository = InMemoryTransactionRepository()
    events = InMemoryTransactionEventPublisher()
    receive = ReceiveTransactionUseCase(repository, events)
    cases = InMemoryCaseQueue()
    cases.stop_consumer()

    accepted = []
    for _ in range(3):
        out = receive.execute(_input())
        accepted.append(out)
        _scoring(cases).execute(
            transaction_from_event(_force_event_timestamp(events.published[-1]))
        )

    assert len(accepted) == 3
    assert all(a.status == "accepted" for a in accepted)
    assert len(cases.published) == 3
    assert len(cases.pending) == 3
    assert cases.consumed == []


def test_pending_cases_are_processed_without_loss_when_consumer_restarts() -> None:
    """Al reactivar el consumidor, todos los casos pendientes se procesan."""
    repository = InMemoryTransactionRepository()
    events = InMemoryTransactionEventPublisher()
    receive = ReceiveTransactionUseCase(repository, events)
    cases = InMemoryCaseQueue()
    cases.stop_consumer()

    n = 5
    for _ in range(n):
        receive.execute(_input())
        _scoring(cases).execute(
            transaction_from_event(_force_event_timestamp(events.published[-1]))
        )

    assert len(cases.pending) == n
    assert cases.consumed == []

    cases.start_consumer()

    assert cases.pending == []
    assert len(cases.consumed) == n
    assert len(cases.published) == n
    consumed_ids = {c.transaction_id for c in cases.consumed}
    published_ids = {c.transaction_id for c in cases.published}
    assert consumed_ids == published_ids
