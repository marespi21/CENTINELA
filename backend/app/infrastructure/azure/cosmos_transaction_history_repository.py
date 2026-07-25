"""Historial de transacciones sobre Cosmos DB (Semana 3).

Lee las transacciones previas de una cuenta desde el contenedor NoSQL,
particionado por `/accountId` (una sola partición por consulta; ver
docs/nosql.md). Reemplaza a `InMemoryTransactionHistoryRepository` en el
composition root del worker cuando `COSMOS_ENDPOINT` está configurado.

Los documentos de transacción se distinguen por `docType == "transaction"`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.domain.entities.transaction import Transaction
from app.domain.repositories.transaction_history_repository import (
    TransactionHistoryRepository,
)
from app.infrastructure.azure.cosmos_client import get_container_client

TRANSACTION_DOC_TYPE = "transaction"


def _to_transaction(doc: dict[str, Any]) -> Transaction:
    """Documento Cosmos (camelCase) -> entidad Transaction."""
    raw_ts = str(doc["timestamp"]).replace("Z", "+00:00")
    ts = datetime.fromisoformat(raw_ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return Transaction(
        transaction_id=UUID(str(doc["transactionId"])),
        account_id=str(doc["accountId"]),
        amount=Decimal(str(doc["amount"])),
        currency=str(doc["currency"]).upper(),
        merchant_id=str(doc["merchantId"]),
        merchant_category=str(doc["merchantCategory"]),
        timestamp=ts,
        latitude=Decimal(str(doc["latitude"])),
        longitude=Decimal(str(doc["longitude"])),
    )


class CosmosTransactionHistoryRepository(TransactionHistoryRepository):
    def __init__(
        self,
        endpoint: str = "",
        database: str = "",
        container: str = "",
        key: str | None = None,
        container_client: Any | None = None,
    ) -> None:
        # `container_client` permite inyectar un cliente (o un doble en pruebas);
        # si no se pasa, se construye desde la configuración.
        self._container = container_client or get_container_client(
            endpoint, database, container, key
        )

    def history_for_account(self, account_id: str) -> list[Transaction]:
        query = (
            "SELECT * FROM c WHERE c.accountId = @acc "
            "AND c.docType = @docType ORDER BY c.timestamp ASC"
        )
        items = self._container.query_items(
            query=query,
            parameters=[
                {"name": "@acc", "value": account_id},
                {"name": "@docType", "value": TRANSACTION_DOC_TYPE},
            ],
            partition_key=account_id,
        )
        return [_to_transaction(doc) for doc in items]
