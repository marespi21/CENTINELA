from __future__ import annotations

from itertools import count

from app.domain.repositories.document_queue import DocumentQueue, QueueMessage


class InMemoryQueue(DocumentQueue):
    """Cola en memoria.

    Permite desarrollar y probar el flujo de eventos sin Azure Queue.
    Se reemplaza por AzureQueueService cambiando solo el composition root.
    """

    def __init__(self) -> None:
        self._messages: list[QueueMessage] = []
        self._ids = count(1)

    def send_message(self, content: str) -> None:
        message_id = str(next(self._ids))
        self._messages.append(
            QueueMessage(
                message_id=message_id,
                pop_receipt=message_id,
                content=content,
            )
        )

    def receive_messages(self, max_messages: int = 1) -> list[QueueMessage]:
        return self._messages[:max_messages]

    def delete_message(self, message: QueueMessage) -> None:
        self._messages = [
            m for m in self._messages if m.message_id != message.message_id
        ]
