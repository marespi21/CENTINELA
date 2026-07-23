from __future__ import annotations

from app.domain.entities.scoring_result import ScoringResult
from app.domain.repositories.case_queue import CaseQueue


class InMemoryCaseQueue(CaseQueue):
    """Cola de casos en memoria (desarrollo/pruebas).

    Se reemplaza por Azure Queue en el composition root. Conserva los casos
    publicados para poder verificarlos en las pruebas.
    """

    def __init__(self) -> None:
        self.published: list[ScoringResult] = []

    def publish_case(self, result: ScoringResult) -> None:
        self.published.append(result)
