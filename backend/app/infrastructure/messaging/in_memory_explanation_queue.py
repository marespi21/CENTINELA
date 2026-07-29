"""Cola de enriquecimiento en memoria (desarrollo/pruebas)."""

from __future__ import annotations

from app.application.dtos.explanation_request import ExplanationRequested
from app.domain.repositories.explanation_queue import ExplanationQueue


class InMemoryExplanationQueue(ExplanationQueue):
    def __init__(self) -> None:
        self.requests: list[ExplanationRequested] = []

    def request_enrichment(
        self, case_id: str, transaction_id: str, account_id: str
    ) -> None:
        self.requests.append(
            ExplanationRequested(
                case_id=case_id,
                transaction_id=transaction_id,
                account_id=account_id,
            )
        )
