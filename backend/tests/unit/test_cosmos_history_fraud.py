"""Historial real en Cosmos para el motor de fraude (módulo Camila).

Criterios:
- Al ingresar, la transacción se persiste en Cosmos por cuenta.
- El motor lee ese historial y la regla de velocidad se dispara con varias
  transacciones reales de la misma cuenta.
- Sin secretos: se usan dobles de contenedor (no COSMOS_KEY en tests).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.application.dtos.transaction_dto import ReceiveTransactionInput
from app.application.use_cases.receive_transaction import ReceiveTransactionUseCase
from app.application.use_cases.score_transaction import ScoreTransactionUseCase
from app.domain.entities.transaction import Transaction
from app.domain.services.rules import RULE_VELOCITY
from app.domain.value_objects.scoring_config import ScoringConfig
from app.infrastructure.azure.cosmos_transaction_history_repository import (
    TRANSACTION_DOC_TYPE,
    CosmosTransactionHistoryRepository,
)
from app.infrastructure.azure.cosmos_transaction_repository import (
    CosmosTransactionRepository,
    transaction_to_document,
)
from app.infrastructure.messaging.in_memory_case_queue import InMemoryCaseQueue
from app.infrastructure.messaging.in_memory_transaction_event_publisher import (
    InMemoryTransactionEventPublisher,
)
from app.infrastructure.repositories.in_memory_score_repository import (
    InMemoryScoreRepository,
)

NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)
ACCOUNT = "acc-historial-001"
_LAT, _LON = Decimal("4.7110"), Decimal("-74.0721")


class _FakeCosmosContainer:
    """Doble in-memory del contenedor Cosmos (sin SDK ni secretos)."""

    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self.last_query: dict[str, Any] = {}

    def upsert_item(self, doc: dict[str, Any]) -> None:
        for i, existing in enumerate(self.items):
            if existing.get("id") == doc.get("id") and existing.get("accountId") == doc.get(
                "accountId"
            ):
                self.items[i] = doc
                return
        self.items.append(doc)

    def query_items(
        self,
        query: str,
        parameters: list[dict[str, Any]],
        partition_key: str | None = None,
        enable_cross_partition_query: bool = False,
    ):
        self.last_query = {
            "query": query,
            "parameters": parameters,
            "pk": partition_key,
            "cross": enable_cross_partition_query,
        }
        params = {p["name"]: p["value"] for p in parameters}
        docs = list(self.items)

        if partition_key is not None:
            docs = [d for d in docs if d.get("accountId") == partition_key]

        if "@docType" in params:
            docs = [d for d in docs if d.get("docType") == params["@docType"]]
        if "@acc" in params:
            docs = [d for d in docs if d.get("accountId") == params["@acc"]]
        if "@txId" in params:
            docs = [d for d in docs if d.get("transactionId") == params["@txId"]]

        if "COUNT(1)" in query.upper():
            return [len(docs)]

        return sorted(docs, key=lambda d: d.get("timestamp", ""))


def _tx(
    *,
    minutes_ago: int = 0,
    amount: str = "100",
    tx_id: UUID | None = None,
    account_id: str = ACCOUNT,
) -> Transaction:
    return Transaction(
        transaction_id=tx_id or uuid4(),
        account_id=account_id,
        amount=Decimal(amount),
        currency="COP",
        merchant_id="mer-1",
        merchant_category="restaurants",
        timestamp=NOW - timedelta(minutes=minutes_ago),
        latitude=_LAT,
        longitude=_LON,
    )


def test_persist_transaction_in_cosmos_by_account() -> None:
    """Al ingresar, se persiste en Cosmos particionado por cuenta."""
    fake = _FakeCosmosContainer()
    repo = CosmosTransactionRepository(container_client=fake)
    events = InMemoryTransactionEventPublisher()
    use_case = ReceiveTransactionUseCase(repository=repo, event_publisher=events)

    tx_id = uuid4()
    result = use_case.execute(
        ReceiveTransactionInput(
            transaction_id=tx_id,
            account_id=ACCOUNT,
            amount=Decimal("150.00"),
            currency="cop",
            merchant_id="mer-9",
            merchant_category="restaurants",
            latitude=_LAT,
            longitude=_LON,
        )
    )

    assert result.status == "accepted"
    assert len(fake.items) == 1
    doc = fake.items[0]
    assert doc["docType"] == TRANSACTION_DOC_TYPE
    assert doc["accountId"] == ACCOUNT
    assert doc["transactionId"] == str(tx_id)
    assert doc["id"] == str(tx_id)
    assert doc["amount"] == "150.00"
    assert "timestamp" in doc
    # Alimenta el mismo contrato que lee el historial del motor.
    assert transaction_to_document(_tx(tx_id=tx_id))["docType"] == TRANSACTION_DOC_TYPE


def test_exists_detects_duplicate_in_cosmos() -> None:
    fake = _FakeCosmosContainer()
    repo = CosmosTransactionRepository(container_client=fake)
    tx = _tx()
    repo.save(tx)

    assert repo.exists(tx.transaction_id) is True
    assert repo.exists(uuid4()) is False
    assert fake.last_query["cross"] is True


def test_velocity_fraud_uses_real_account_history_from_cosmos() -> None:
    """Varias txs reales de la misma cuenta en Cosmos disparan velocidad."""
    fake = _FakeCosmosContainer()
    write = CosmosTransactionRepository(container_client=fake)
    history_repo = CosmosTransactionHistoryRepository(container_client=fake)

    # 4 previas en la ventana + la actual = 5 → umbral de velocidad.
    priors = [_tx(minutes_ago=m) for m in (1, 2, 3, 4)]
    for prior in priors:
        write.save(prior)

    current = _tx(minutes_ago=0, amount="100")
    # El historial que lee el motor viene de Cosmos (misma cuenta).
    loaded = history_repo.history_for_account(ACCOUNT)
    assert len(loaded) == 4
    assert all(t.account_id == ACCOUNT for t in loaded)
    assert fake.last_query["pk"] == ACCOUNT

    cases = InMemoryCaseQueue()
    scoring = ScoreTransactionUseCase(
        history_repository=history_repo,
        score_repository=InMemoryScoreRepository(),
        case_queue=cases,
        config=ScoringConfig(velocity_max_tx=5, velocity_window_minutes=10),
    )
    result = scoring.execute(current)

    velocity = next(r for r in result.rule_results if r.rule_id == RULE_VELOCITY)
    assert velocity.triggered is True
    assert velocity.observed["count_in_window"] == 5
    assert velocity.points > 0
