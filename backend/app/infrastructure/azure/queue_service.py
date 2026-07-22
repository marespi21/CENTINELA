from __future__ import annotations

from app.domain.repositories.document_queue import DocumentQueue, QueueMessage


class AzureQueueService(DocumentQueue):
    """Adaptador de Azure Queue Storage.

    Se activa reemplazando InMemoryQueue en el composition root
    (presentation/api/dependencies/documents.py) cuando la Queue exista.

    Autenticación: igual que AzureBlobStorage (connection_string o
    account_url + Managed Identity). El SDK se importa de forma perezosa.
    """

    def __init__(
        self,
        queue_name: str,
        connection_string: str | None = None,
        account_url: str | None = None,
    ) -> None:
        from azure.storage.queue import QueueClient

        if connection_string:
            self._client = QueueClient.from_connection_string(
                connection_string, queue_name
            )
        elif account_url:
            from azure.identity import DefaultAzureCredential

            self._client = QueueClient(
                account_url=account_url,
                queue_name=queue_name,
                credential=DefaultAzureCredential(),
            )
        else:
            raise ValueError("connection_string or account_url is required")

    def send_message(self, content: str) -> None:
        self._client.send_message(content)

    def receive_messages(self, max_messages: int = 1) -> list[QueueMessage]:
        received = self._client.receive_messages(max_messages=max_messages)
        return [
            QueueMessage(
                message_id=message.id,
                pop_receipt=message.pop_receipt,
                content=message.content,
            )
            for message in received
        ]

    def delete_message(self, message: QueueMessage) -> None:
        self._client.delete_message(message.message_id, message.pop_receipt)
