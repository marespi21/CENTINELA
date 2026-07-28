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
    assigned_to: str | None = Field(
        default=None, alias="assignedTo", serialization_alias="assignedTo"
    )
    explanation: ExplanationSchema
    audit_trail: list[dict[str, Any]] = Field(
        default_factory=list, alias="auditTrail", serialization_alias="auditTrail"
    )


class CaseSummaryResponse(BaseModel):
    """Fila de la bandeja de casos (GET /cases)."""

    model_config = ConfigDict(populate_by_name=True)

    case_id: str = Field(alias="caseId", serialization_alias="caseId")
    transaction_id: str = Field(alias="transactionId", serialization_alias="transactionId")
    account_id: str = Field(alias="accountId", serialization_alias="accountId")
    status: str
    opened_at: datetime = Field(alias="openedAt", serialization_alias="openedAt")
    score: int
    is_case: bool = Field(alias="isCase", serialization_alias="isCase")
    summary: str
    assigned_to: str | None = Field(
        default=None, alias="assignedTo", serialization_alias="assignedTo"
    )


class CaseListResponse(BaseModel):
    """Respuesta paginada de GET /cases."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[CaseSummaryResponse] = Field(default_factory=list)
    total: int
    page: int
    page_size: int = Field(alias="pageSize", serialization_alias="pageSize")


class CaseDocumentResponse(BaseModel):
    """Documento de un caso con su URL temporal (SAS) para abrirlo."""

    model_config = ConfigDict(populate_by_name=True)

    blob_name: str = Field(alias="blobName", serialization_alias="blobName")
    filename: str
    content_type: str = Field(alias="contentType", serialization_alias="contentType")
    url: str
    expires_at: datetime = Field(alias="expiresAt", serialization_alias="expiresAt")


class CaseDocumentListResponse(BaseModel):
    """Respuesta de GET /cases/{caseId}/documents."""

    model_config = ConfigDict(populate_by_name=True)

    items: list[CaseDocumentResponse] = Field(default_factory=list)


class AssignCaseRequest(BaseModel):
    """Cuerpo de POST /cases/{caseId}/assign."""

    model_config = ConfigDict(populate_by_name=True)

    assignee_id: str | None = Field(default=None, alias="assigneeId")


class ResolveCaseRequest(BaseModel):
    """Cuerpo de POST /cases/{caseId}/resolve."""

    model_config = ConfigDict(populate_by_name=True)

    resolution: str = Field(min_length=1)
    note: str | None = None
