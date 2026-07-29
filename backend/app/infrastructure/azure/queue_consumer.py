"""Consumidor de Azure Queue Storage para el worker contenedorizado.

Autenticación idéntica al resto de adaptadores: connection string (local) o
Managed Identity vía `account_url` (producción). El SDK se importa de forma
perezosa para no cargarlo en procesos que no lo usan.
"""

from __future__ import annotations

import logging

from app.domain.repositories.message_consumer import MessageConsumer, ReceivedMessage

logger = logging.getLogger(__name__)

POISON_SUFFIX = "-poison"


class AzureQueueConsumer(MessageConsumer):
    """Lee de una cola de Azure Storage y aparta los mensajes envenenados.

    Replica la convención de Azure Functions: los mensajes que superan el
    máximo de entregas se copian a `<cola>-poison` y se borran de la principal,
    de modo que un mensaje corrupto no bloquea la cola para siempre.
    """

    def __init__(
        self,
        queue_name: str,
        connection_string: str | None = None,
        account_url: str | None = None,
    ) -> None:
        self._queue_name = queue_name
        self._connection_string = connection_string
        self._account_url = account_url
        self._client = self._build_client(queue_name)
        self._poison_client = None

    def _build_client(self, queue_name: str):  # noqa: ANN202 - tipo del SDK
        from azure.storage.queue import QueueClient

        if self._connection_string:
            return QueueClient.from_connection_string(self._connection_string, queue_name)
        if self._account_url:
            from azure.identity import DefaultAzureCredential

            return QueueClient(
                account_url=self._account_url,
                queue_name=queue_name,
                credential=DefaultAzureCredential(),
            )
        raise ValueError("connection_string or account_url is required")

    def ensure_queue(self) -> None:
        """Crea la cola si no existe (idempotente); no falla si ya está."""
        try:
            self._client.create_queue()
        except Exception:  # noqa: BLE001 - ResourceExistsError y permisos
            logger.debug("la cola %s ya existe o no se pudo crear", self._queue_name)

    def receive(self, max_messages: int, visibility_timeout: int) -> list[ReceivedMessage]:
        received = self._client.receive_messages(
            max_messages=max_messages,
            visibility_timeout=visibility_timeout,
        )
        return [
            ReceivedMessage(
                message_id=message.id,
                pop_receipt=message.pop_receipt,
                content=message.content,
                dequeue_count=message.dequeue_count or 1,
            )
            for message in received
        ]

    def delete(self, message: ReceivedMessage) -> None:
        self._client.delete_message(message.message_id, message.pop_receipt)

    def dead_letter(self, message: ReceivedMessage) -> None:
        if self._poison_client is None:
            self._poison_client = self._build_client(self._queue_name + POISON_SUFFIX)
            try:
                self._poison_client.create_queue()
            except Exception:  # noqa: BLE001 - ya existe
                logger.debug("la cola poison de %s ya existe", self._queue_name)
        self._poison_client.send_message(message.content)
        self.delete(message)
        logger.error(
            "mensaje envenenado apartado queue=%s%s message_id=%s entregas=%s",
            self._queue_name,
            POISON_SUFFIX,
            message.message_id,
            message.dequeue_count,
        )
