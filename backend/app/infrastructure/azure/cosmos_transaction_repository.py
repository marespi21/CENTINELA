"""Persistencia de transacciones en Cosmos DB (módulo Camila).

Al ingresar una transacción, la API la guarda en el contenedor NoSQL
particionado por `/accountId`. Ese historial es el que lee el motor de fraude
para reglas de velocidad y montos atípicos.

Misma forma de documento que `CosmosTransactionHistoryRepository` (`docType`
= `transaction`). Sin secretos en código: Managed Identity o `COSMOS_KEY`
vía configuración / Key Vault.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any
from uuid import UUID

from app.domain.entities.transaction import Transaction
from app.domain.repositories.transaction_repository import TransactionRepository
from app.infrastructure.azure.cosmos_client import get_container_client
from app.infrastructure.azure.cosmos_transaction_history_repository import (
    TRANSACTION_DOC_TYPE,
)


def transaction_to_document(transaction: Transaction) -> dict[str, Any]:
    """Transaction -> documento Cosmos (camelCase, pk accountId)."""
    ts = transaction.timestamp
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return {
        "id": str(transaction.transaction_id),
        "docType": TRANSACTION_DOC_TYPE,
        "transactionId": str(transaction.transaction_id),
        "accountId": transaction.account_id,
        "amount": str(transaction.amount),
        "currency": transaction.currency,
        "merchantId": transaction.merchant_id,
        "merchantCategory": transaction.merchant_category,
        "timestamp": ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "latitude": str(transaction.latitude),
        "longitude": str(transaction.longitude),
    }


class CosmosTransactionRepository(TransactionRepository):
    """Escribe transacciones en Cosmos para alimentar el historial por cuenta."""

    def __init__(
        self,
        endpoint: str = "",
        database: str = "",
        container: str = "",
        key: str | None = None,
        container_client: Any | None = None,
    ) -> None:
        self._container = container_client or get_container_client(
            endpoint, database, container, key
        )

    def save(self, transaction: Transaction) -> None:
        self._container.upsert_item(transaction_to_document(transaction))

    def exists(self, transaction_id: UUID) -> bool:
        """Deduplica por transactionId (consulta cross-partition)."""
        query = (
            "SELECT VALUE COUNT(1) FROM c "
            "WHERE c.transactionId = @txId AND c.docType = @docType"
        )
        parameters = [
            {"name": "@txId", "value": str(transaction_id)},
            {"name": "@docType", "value": TRANSACTION_DOC_TYPE},
        ]
        items = list(
            self._container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        )
        return bool(items) and int(items[0]) > 0
