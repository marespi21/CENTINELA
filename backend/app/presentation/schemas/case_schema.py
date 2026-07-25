"""Schemas HTTP de la API de revisión de casos (Semana 3).

Fijan el contrato de salida de `GET /cases/{caseId}`: el caso, su explicación
legible y su traza de auditoría. Gestión de casos rellena estos datos; seguridad
protege el endpoint. La forma NO cambia sin acordarlo.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExplanationReasonSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rule_id: str = Field(alias="ruleId", serialization_alias="ruleId")
    title: str
    description: str
    detail: str
    points: int
    observed: dict[str, Any] = Field(default_factory=dict)


class ExplanationSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    transaction_id: str = Field(alias="transactionId", serialization_alias="transactionId")
    account_id: str = Field(alias="accountId", serialization_alias="accountId")
    score: int
    threshold: int
    is_case: bool = Field(alias="isCase", serialization_alias="isCase")
    summary: str
    generated_at: datetime = Field(alias="generatedAt", serialization_alias="generatedAt")
    reasons: list[ExplanationReasonSchema] = Field(default_factory=list)


class CaseDetailResponse(BaseModel):
    """Respuesta de GET /cases/{caseId}."""

    model_config = ConfigDict(populate_by_name=True)

    case_id: str = Field(alias="caseId", serialization_alias="caseId")
    transaction_id: str = Field(alias="transactionId", serialization_alias="transactionId")
    account_id: str = Field(alias="accountId", serialization_alias="accountId")
    status: str
    opened_at: datetime = Field(alias="openedAt", serialization_alias="openedAt")
    explanation: ExplanationSchema
    audit_trail: list[dict[str, Any]] = Field(
        default_factory=list, alias="auditTrail", serialization_alias="auditTrail"
    )
