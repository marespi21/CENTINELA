from __future__ import annotations

from app.domain.entities.scoring_result import ScoringResult
from app.domain.repositories.case_queue import CaseQueue


class InMemoryCaseQueue(CaseQueue):
    """Cola de casos en memoria con semántica durable para pruebas.

    - `publish_case` siempre encola (el mensaje no se pierde).
    - Si el consumidor está detenido, los casos quedan en `pending`.
    - Al reactivar (`start_consumer`), se drenan sin pérdida.
    En producción se reemplaza por Azure Queue en el composition root.
    """

    def __init__(self) -> None:
        self.published: list[ScoringResult] = []
        self.pending: list[ScoringResult] = []
        self.consumed: list[ScoringResult] = []
        self.consumer_enabled: bool = True

    def publish_case(self, result: ScoringResult) -> None:
        self.published.append(result)
        self.pending.append(result)
        if self.consumer_enabled:
            self._drain()

    def stop_consumer(self) -> None:
        """Simula consumidor caído: los mensajes permanecen en la cola."""
        self.consumer_enabled = False

    def start_consumer(self) -> None:
        """Reactiva el consumidor y procesa todos los casos pendientes."""
        self.consumer_enabled = True
        self._drain()

    def _drain(self) -> None:
        while self.pending:
            self.consumed.append(self.pending.pop(0))
