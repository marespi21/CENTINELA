"""Azure Queue Storage client wrapper.

A thin gateway over ``azure-storage-queue``. Messages are Base64-encoded on the
wire via :class:`TextBase64EncodePolicy` because the Week 2 Azure Functions
queue trigger expects Base64-encoded messages by default.
"""

from __future__ import annotations

from azure.core.exceptions import ResourceExistsError
from azure.storage.queue import (
    QueueClient,
    TextBase64DecodePolicy,
    TextBase64EncodePolicy,
)

from app.core.logger import get_logger

logger = get_logger(__name__)


class QueueStorageClient:
    """Minimal Queue Storage gateway (ensure queue, send Base64 messages)."""

    def __init__(self, connection_string: str, queue_name: str) -> None:
        self._connection_string = connection_string
        self._queue_name = queue_name
        self._client: QueueClient | None = None

    @property
    def client(self) -> QueueClient:
        if self._client is None:
            self._client = QueueClient.from_connection_string(
                self._connection_string,
                self._queue_name,
                message_encode_policy=TextBase64EncodePolicy(),
                message_decode_policy=TextBase64DecodePolicy(),
            )
        return self._client

    def ensure_queue(self) -> None:
        """Create the queue if it does not already exist (idempotent)."""
        try:
            self.client.create_queue()
            logger.info("Created queue", extra={"queue": self._queue_name})
        except ResourceExistsError:
            pass

    def send_message(self, content: str) -> None:
        """Send a message; the encode policy Base64-encodes it automatically."""
        self.ensure_queue()
        self.client.send_message(content)
        logger.info("Sent queue message", extra={"queue": self._queue_name})

    def check_connectivity(self) -> bool:
        """Best-effort connectivity probe used by the health endpoint."""
        try:
            self.ensure_queue()
            self.client.get_queue_properties()
            return True
        except Exception:  # noqa: BLE001 - a health probe must never raise
            logger.warning("Queue storage connectivity check failed")
            return False
