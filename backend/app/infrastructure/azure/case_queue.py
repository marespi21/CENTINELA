from __future__ import annotations

import json
from datetime import timezone

from app.application.dtos.explanation_dto import serialize_explanation
from app.domain.entities.explanation import Explanation
from app.domain.entities.scoring_result import ScoringResult
from app.domain.repositories.case_queue import CaseQueue
from app.infrastructure.azure.queue_service import AzureQueueService


class AzureCaseQueue(CaseQueue):
    """Cola durable de casos (scoring → gestión de casos).

    Azure Queue Storage garantiza entrega: si el consumidor está caído, los
    mensajes permanecen hasta que se procesen. No se pierde ningún caso.
    """

    def __init__(
        self,
        queue_name: str,
        connection_string: str | None = None,
        account_url: str | None = None,
    ) -> None:
        self._queue = AzureQueueService(
            queue_name=queue_name,
            connection_string=connection_string,
            account_url=account_url,
        )

    def publish_case(
        self, result: ScoringResult, explanation: Explanation | None = None
    ) -> None:
        self._queue.send_message(_serialize_case(result, explanation))


def _serialize_case(
    result: ScoringResult, explanation: Explanation | None = None
) -> str:
    """Contrato JSON del mensaje de caso (camelCase).

    Incluye el bloque `explanation` cuando el motor adjunta la explicación
    legible (contrato compartido con gestión de casos, ver explainability.md).
    """
    scored_at = result.scored_at
    if scored_at.tzinfo is None:
        scored_at = scored_at.replace(tzinfo=timezone.utc)
    message = {
        "event": "case.opened",
        "transactionId": str(result.transaction_id),
        "accountId": result.account_id,
        "score": result.score,
        "threshold": result.threshold,
        "scoredAt": scored_at.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "triggeredRules": [
            {
                "ruleId": rule.rule_id,
                "points": rule.points,
                "observed": rule.observed,
            }
            for rule in result.triggered_rules
        ],
    }
    if explanation is not None:
        message["explanation"] = serialize_explanation(explanation)
    return json.dumps(message)
