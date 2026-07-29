"""Puerto de consumo de colas para el worker contenedorizado (Sprint 6, Fase 1).

`DocumentQueue` ya modela publicar/leer/borrar, pero no expone el contador de
entregas (`dequeue_count`) ni el *visibility timeout*, y ambos son necesarios
para reproducir en un contenedor el comportamiento que Azure Functions daba
gratis: reintento automático del mensaje y desvío a la cola *poison* cuando un
mensaje falla demasiadas veces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ReceivedMessage:
    """Mensaje tomado de la cola, aún no eliminado.

    `dequeue_count` es cuántas veces se ha entregado ya: permite detectar
    mensajes envenenados que fallan una y otra vez.
    """

    message_id: str
    pop_receipt: str
    content: str
    dequeue_count: int


class MessageConsumer(ABC):
    """Consumidor de una cola concreta."""

    @abstractmethod
    def receive(self, max_messages: int, visibility_timeout: int) -> list[ReceivedMessage]:
        """Toma hasta `max_messages`, ocultándolos `visibility_timeout` segundos."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, message: ReceivedMessage) -> None:
        """Elimina definitivamente un mensaje ya procesado."""
        raise NotImplementedError

    @abstractmethod
    def dead_letter(self, message: ReceivedMessage) -> None:
        """Aparta un mensaje envenenado y lo elimina de la cola principal."""
        raise NotImplementedError
