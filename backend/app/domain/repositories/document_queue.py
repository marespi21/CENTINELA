from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class QueueMessage:
    """Mensaje recibido de la cola.

    pop_receipt es necesario para poder eliminar el mensaje en Azure Queue.
    """

    message_id: str
    pop_receipt: str
    content: str


class DocumentQueue(ABC):
    """Puerto de cola de eventos de documentos.

    La implementación concreta (memoria, Azure Queue Storage) vive en
    infrastructure.
    """

    @abstractmethod
    def send_message(self, content: str) -> None:
        """Publica un mensaje en la cola."""
        raise NotImplementedError

    @abstractmethod
    def receive_messages(self, max_messages: int = 1) -> list[QueueMessage]:
        """Lee hasta max_messages mensajes sin eliminarlos."""
        raise NotImplementedError

    @abstractmethod
    def delete_message(self, message: QueueMessage) -> None:
        """Elimina un mensaje ya procesado."""
        raise NotImplementedError
