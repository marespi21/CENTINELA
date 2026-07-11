"""Repository for persisting and publishing transactions.

Bridges the domain model to the Azure Storage gateways: writes the transaction
as a JSON blob and publishes it as a queue message.
"""

from __future__ import annotations

import json

from app.infrastructure.azure.blob import BlobStorageClient
from app.infrastructure.azure.queue import QueueStorageClient
from app.models.transaction import Transaction


class TransactionRepository:
    """Stores transactions in Blob Storage and publishes them to the queue."""

    def __init__(
        self,
        blob: BlobStorageClient,
        queue: QueueStorageClient,
        container: str,
    ) -> None:
        self._blob = blob
        self._queue = queue
        self._container = container

    def save(self, transaction: Transaction) -> str:
        """Store the transaction as a JSON blob; return the blob name."""
        blob_name = f"{transaction.transaction_id}.json"
        return self._blob.upload_json(
            self._container, blob_name, transaction.to_storage_dict()
        )

    def publish(self, transaction: Transaction) -> None:
        """Publish the transaction as a (Base64-encoded) queue message."""
        self._queue.send_message(json.dumps(transaction.to_storage_dict()))
