"""Persistencia de scores sobre Cosmos DB (Semana 3).

Guarda el resultado del scoring (puntaje, umbral, detalle por regla) en el mismo
contenedor NoSQL, particionado por `/accountId`. Los documentos de score se
distinguen por `docType == "score"`. Reemplaza a `InMemoryScoreRepository` en el
composition root del worker cuando `COSMOS_ENDPOINT` está configurado.
"""

from __future__ import annotations

from datetime import timezone
from typing import Any

from app.domain.entities.scoring_result import ScoringResult
from app.domain.repositories.score_repository import ScoreRepository
from app.infrastructure.azure.cosmos_client import get_container_client

SCORE_DOC_TYPE = "score"


def _to_document(result: ScoringResult) -> dict[str, Any]:
    """ScoringResult -> documento Cosmos (camelCase)."""
    scored_at = result.scored_at
    if scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=timezone.utc)
    return {
        # id único del score; separado del doc de la transacción (mismo id lógico).
        "id": f"score:{result.transaction_id}",
        "docType": SCORE_DOC_TYPE,
        "transactionId": str(result.transaction_id),
        "accountId": result.account_id,
        "score": result.score,
        "threshold": result.threshold,
        "isCase": result.is_case,
        "scoredAt": scored_at.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "ruleResults": [
            {
                "ruleId": rule.rule_id,
                "triggered": rule.triggered,
                "points": rule.points,
                "observed": rule.observed,
            }
            for rule in result.rule_results
        ],
    }


class CosmosScoreRepository(ScoreRepository):
    def __init__(
        self,
        endpoint: str = "",
        database: str = "",
        container: str = "",
        key: str | None = None,
        container_client: Any | None = None,
    ) -> None:
        # `container_client` permite inyectar un cliente (o un doble en pruebas);
        # si no se pasa, se construye desde la configuración.
        self._container = container_client or get_container_client(
            endpoint, database, container, key
        )

    def save(self, result: ScoringResult) -> None:
        self._container.upsert_item(_to_document(result))
