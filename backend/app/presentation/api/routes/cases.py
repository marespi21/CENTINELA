"""API de revisión de casos (Semana 3, módulos Juan José + Lucas).

`GET /cases/{caseId}` devuelve el caso con su explicación legible y su traza de
auditoría. `GET /cases/{caseId}/documents/{blobName}` entrega una URL temporal
(SAS delegada) para ver un documento de verificación sin exponer el contenedor.

Ambos endpoints son de lectura y exigen rol Analista, Auditor o Administrador
(401 sin clave, 403 con rol no autorizado). Con AUTH_ENABLED=false (local) no
bloquean.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.dtos.explanation_dto import serialize_explanation
from app.domain.exceptions.case_exceptions import CaseNotFoundError
from app.domain.repositories.case_read_repository import CaseDetail, CaseReadRepository
from app.domain.repositories.document_access_provider import DocumentAccessProvider
from app.domain.value_objects.role import Role
from app.presentation.api.dependencies.cases import get_case_read_repository
from app.presentation.api.dependencies.document_access import (
    get_document_access_provider,
)
from app.presentation.api.dependencies.security import Principal, require_roles
from app.presentation.schemas.case_schema import CaseDetailResponse, ExplanationSchema
from app.presentation.schemas.document_access_schema import DocumentAccessResponse

router = APIRouter(prefix="/cases", tags=["cases"])

# Lectura de casos: analista, auditor o administrador.
_read_case = require_roles(Role.ANALISTA, Role.AUDITOR, Role.ADMINISTRADOR)


def _to_response(detail: CaseDetail) -> CaseDetailResponse:
    return CaseDetailResponse(
        case_id=detail.case_id,
        transaction_id=detail.transaction_id,
        account_id=detail.account_id,
        status=detail.status,
        opened_at=detail.opened_at,
        explanation=ExplanationSchema.model_validate(
            serialize_explanation(detail.explanation)
        ),
        audit_trail=detail.audit_trail,
    )


@router.get(
    "/{case_id}",
    response_model=CaseDetailResponse,
    summary="Detalle de un caso con su explicación (Semana 3)",
)
async def get_case(
    case_id: str,
    repo: CaseReadRepository = Depends(get_case_read_repository),
    _principal: Principal = Depends(_read_case),
) -> CaseDetailResponse:
    detail = repo.get_case(case_id)
    if detail is None:
        raise CaseNotFoundError(case_id)
    return _to_response(detail)


@router.get(
    "/{case_id}/documents/{blob_name:path}",
    response_model=DocumentAccessResponse,
    summary="URL temporal (SAS) para un documento del caso (Semana 3)",
)
async def get_case_document_access(
    case_id: str,
    blob_name: str,
    provider: DocumentAccessProvider = Depends(get_document_access_provider),
    _principal: Principal = Depends(_read_case),
) -> DocumentAccessResponse:
    access = provider.temporary_read_url(blob_name)
    return DocumentAccessResponse(url=access.url, expires_at=access.expires_at)
