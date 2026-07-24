from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.application.dtos.scoring_dto import transaction_from_event
from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.application.use_cases.score_transaction import ScoreTransactionUseCase
from app.domain.entities.transaction import Transaction
from app.domain.value_objects.scoring_config import ScoringConfig
from app.infrastructure.messaging.in_memory_case_queue import InMemoryCaseQueue
from app.infrastructure.repositories.in_memory_score_repository import (
    InMemoryScoreRepository,
)
from app.infrastructure.repositories.in_memory_transaction_history_repository import (
    InMemoryTransactionHistoryRepository,
)

NOW = datetime(2026, 7, 23, 12, 0, 0, tzinfo=timezone.utc)
BOGOTA = (Decimal("4.7110"), Decimal("-74.0721"))
TOKYO = (Decimal("35.6762"), Decimal("139.6503"))

CONFIG = ScoringConfig(
    threshold=50,
    weight_geo_impossible=45,
    weight_risky_merchant=20,
    risky_categories=frozenset({"crypto"}),
)


def _event(*, category="crypto", coords=TOKYO) -> str:
    """Evento de transacción serializado, tal como llega por la cola."""
    lat, lon = coords
    return json.dumps(
        {
            "transactionId": str(uuid4()),
            "accountId": "acc-001",
            "amount": "100",
            "currency": "COP",
            "merchantId": "mer-1",
            "merchantCategory": category,
            "timestamp": NOW.isoformat(),
            "latitude": str(lat),
            "longitude": str(lon),
        }
    )


def _prior_bogota() -> Transaction:
    return Transaction(
        transaction_id=uuid4(),
        account_id="acc-001",
        amount=Decimal("100"),
        currency="COP",
        merchant_id="mer-0",
        merchant_category="restaurants",
        timestamp=NOW - timedelta(minutes=10),
        latitude=BOGOTA[0],
        longitude=BOGOTA[1],
    )


def _build(config: ScoringConfig):
    history = InMemoryTransactionHistoryRepository([_prior_bogota()])
    scores = InMemoryScoreRepository()
    cases = InMemoryCaseQueue()
    use_case = ScoreTransactionUseCase(history, scores, cases, config)
    return use_case, scores, cases


def test_reacts_to_event_persists_score_and_detail_and_publishes_case() -> None:
    use_case, scores, cases = _build(CONFIG)

    # El motor reacciona a un EVENTO (mensaje de cola), no a una llamada de API.
    transaction = transaction_from_event(_event(category="crypto", coords=TOKYO))
    result = use_case.execute(transaction)

    # Persiste score + detalle con los valores concretos observados.
    saved = scores.get(transaction.transaction_id)
    assert saved is not None
    assert saved.score == 65
    assert saved.is_case is True
    geo = next(r for r in saved.triggered_rules if r.rule_id == "geo_impossible")
    assert "distance_km" in geo.observed and "implied_speed_kmh" in geo.observed

    # Publica el caso porque supera el umbral.
    assert len(cases.published) == 1
    assert cases.published[0].transaction_id == transaction.transaction_id


def test_threshold_change_without_redeploy_changes_behavior() -> None:
    event = _event(category="crypto", coords=TOKYO)  # score fijo = 65

    # Umbral alto (p. ej. app setting FRAUD_SCORE_THRESHOLD=100): NO abre caso.
    strict = replace(CONFIG, threshold=100)
    uc_strict, _, cases_strict = _build(strict)
    r_strict = uc_strict.execute(transaction_from_event(event))
    assert r_strict.score == 65
    assert r_strict.is_case is False
    assert cases_strict.published == []

    # Mismo evento, umbral bajo (=50): SÍ abre caso. Sin cambiar el código.
    lenient = replace(CONFIG, threshold=50)
    uc_lenient, _, cases_lenient = _build(lenient)
    r_lenient = uc_lenient.execute(transaction_from_event(event))
    assert r_lenient.is_case is True
    assert len(cases_lenient.published) == 1


def test_no_case_published_when_below_threshold() -> None:
    use_case, scores, cases = _build(CONFIG)
    # Solo comercio de riesgo (20) < 50; sin salto geográfico.
    transaction = transaction_from_event(_event(category="crypto", coords=BOGOTA))
    result = use_case.execute(transaction)
    assert result.is_case is False
    assert cases.published == []
    assert scores.get(transaction.transaction_id) is not None  # el score igual se persiste


def test_ingestion_is_decoupled_from_scoring() -> None:
    # La ingesta (API) NO dispara scoring: publica un evento y termina.
    # El scoring se ejecuta por el consumidor de la cola, no desde el use case.
    import inspect

    params = inspect.signature(ReceiveTransactionUseCase.__init__).parameters
    assert set(params) == {"self", "repository", "event_publisher"}
    # No hay dependencia del motor de scoring ni de CaseQueue.
    assert "score" not in "".join(params)
    assert "case_queue" not in params
    assert "ScoreTransaction" not in str(ReceiveTransactionUseCase.__init__.__annotations__)
