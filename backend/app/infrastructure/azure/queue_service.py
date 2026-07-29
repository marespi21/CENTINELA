from __future__ import annotations

from app.domain.repositories.document_queue import DocumentQueue, QueueMessage
from app.infrastructure.observability.propagation import inject_trace_context
from app.infrastructure.observability.telemetry import get_tracer

# Punto único por el que pasa TODO envío a cola del sistema: la publicación de
# transacciones, la de casos y la de documentos construyen su adaptador sobre
# esta clase. Por eso el contexto de traza se inyecta aquí y no en cada
# productor: una sola línea cubre las tres colas y no hay forma de olvidarse de
# una al añadir la cuarta.
_tracer = get_tracer("centinela.queue")


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

        self._queue_name = queue_name
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
        # El span de publicación es el padre que el consumidor recuperará al
        # otro lado de la cola: por eso la inyección va DENTRO del span, no
        # antes, o el `traceparent` apuntaría al span equivocado.
        with _tracer.start_as_current_span(f"queue.publish {self._queue_name}") as span:
            span.set_attribute("messaging.system", "azure_queue")
            span.set_attribute("messaging.destination.name", self._queue_name)
            span.set_attribute("messaging.operation", "publish")
            self._client.send_message(inject_trace_context(content))

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
