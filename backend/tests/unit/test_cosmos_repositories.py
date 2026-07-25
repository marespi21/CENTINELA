"""Adaptadores Cosmos DB: mapeo y consulta (Semana 3, módulo Jorge).

Se prueban con un contenedor falso inyectado, sin requerir el SDK ni una cuenta
real: verifican el contrato de documento (camelCase) y la consulta por cuenta.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.entities.rule_result import RuleResult
from app.domain.entities.scoring_result import ScoringResult
from app.infrastructure.azure.cosmos_score_repository import CosmosScoreRepository
from app.infrastructure.azure.cosmos_transaction_history_repository import (
    CosmosTransactionHistoryRepository,
)
from app.domain.services.rules import RULE_VELOCITY

_TX_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


class _FakeContainer:
    """Doble de ContainerProxy: registra la consulta y devuelve/guarda docs."""

    def __init__(self, items: list[dict[str, Any]] | None = None) -> None:
        self._items = items or []
        self.upserted: list[dict[str, Any]] = []
        self.last_query: dict[str, Any] = {}

    def query_items(self, query: str, parameters: list[dict[str, Any]], partition_key: str):
        self.last_query = {"query": query, "parameters": parameters, "pk": partition_key}
        return list(self._items)

    def upsert_item(self, doc: dict[str, Any]) -> None:
        self.upserted.append(doc)


def _tx_doc(tx_id: str, ts: str, amount: str) -> dict[str, Any]:
    return {
        "id": tx_id,
        "docType": "transaction",
        "transactionId": tx_id,
        "accountId": "acc-001",
        "amount": amount,
        "currency": "COP",
        "merchantId": "mer-1",
        "merchantCategory": "restaurants",
        "timestamp": ts,
        "latitude": "4.7110",
        "longitude": "-74.0721",
    }


class TestCosmosHistory:
    def test_maps_documents_to_transactions(self) -> None:
        fake = _FakeContainer([
            _tx_doc("550e8400-e29b-41d4-a716-446655440000", "2026-07-25T12:00:00Z", "100.50"),
            _tx_doc("550e8400-e29b-41d4-a716-446655440001", "2026-07-25T12:05:00Z", "250"),
        ])
        repo = CosmosTransactionHistoryRepository(container_client=fake)

        history = repo.history_for_account("acc-001")

        assert len(history) == 2
        assert history[0].account_id == "acc-001"
        assert history[0].amount == Decimal("100.50")
        assert history[0].timestamp.tzinfo is not None
        # La consulta filtra por cuenta y docType=transaction, y usa la particion.
        assert fake.last_query["pk"] == "acc-001"
        assert "docType" in fake.last_query["query"]
        assert {"name": "@acc", "value": "acc-001"} in fake.last_query["parameters"]

    def test_empty_account_returns_empty(self) -> None:
        repo = CosmosTransactionHistoryRepository(container_client=_FakeContainer([]))
        assert repo.history_for_account("acc-x") == []


class TestCosmosScore:
    def test_save_writes_score_document(self) -> None:
        fake = _FakeContainer()
        repo = CosmosScoreRepository(container_client=fake)
        result = ScoringResult(
            transaction_id=_TX_ID,
            account_id="acc-001",
            score=55,
            threshold=50,
            rule_results=[
                RuleResult(rule_id=RULE_VELOCITY, triggered=True, points=25,
                           observed={"count_in_window": 6}),
            ],
            is_case=True,
            scored_at=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
        )

        repo.save(result)

        assert len(fake.upserted) == 1
        doc = fake.upserted[0]
        assert doc["docType"] == "score"
        assert doc["transactionId"] == str(_TX_ID)
        assert doc["accountId"] == "acc-001"
        assert doc["isCase"] is True
        assert doc["scoredAt"].endswith("Z")
        assert doc["ruleResults"][0]["ruleId"] == RULE_VELOCITY
