"""Contrato de serialización de la explicación (Semana 3).

Fija la forma JSON (camelCase) con la que la explicación viaja por la cola de
casos (mensajería) y se persiste/expone (gestión de casos y API). Es el contrato
compartido: mensajería y casos consumen ESTA estructura.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.domain.entities.explanation import Explanation, ExplanationReason


def serialize_explanation(explanation: Explanation) -> dict[str, Any]:
    """Explicación de dominio → dict JSON (camelCase)."""
    generated_at = explanation.generated_at
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return {
        "transactionId": str(explanation.transaction_id),
        "accountId": explanation.account_id,
        "score": explanation.score,
        "threshold": explanation.threshold,
        "isCase": explanation.is_case,
        "summary": explanation.summary,
        "generatedAt": generated_at.astimezone(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "reasons": [
            {
                "ruleId": reason.rule_id,
                "title": reason.title,
                "description": reason.description,
                "detail": reason.detail,
                "points": reason.points,
                "observed": reason.observed,
            }
            for reason in explanation.reasons
        ],
    }


def explanation_from_dict(data: dict[str, Any]) -> Explanation:
    """dict JSON (camelCase) → Explicación de dominio.

    Inverso de `serialize_explanation`; lo usa gestión de casos para reconstruir
    la explicación persistida (JSONB) al leer un caso.
    """
    raw_ts = str(data["generatedAt"]).replace("Z", "+00:00")
    generated_at = datetime.fromisoformat(raw_ts)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return Explanation(
        transaction_id=UUID(str(data["transactionId"])),
        account_id=str(data["accountId"]),
        score=int(data["score"]),
        threshold=int(data["threshold"]),
        is_case=bool(data["isCase"]),
        summary=str(data["summary"]),
        reasons=[
            ExplanationReason(
                rule_id=str(r["ruleId"]),
                title=str(r["title"]),
                description=str(r.get("description", "")),
                detail=str(r.get("detail", "")),
                points=int(r.get("points", 0)),
                observed=dict(r.get("observed", {})),
            )
            for r in data.get("reasons", [])
        ],
        generated_at=generated_at,
    )
