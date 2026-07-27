"""API de revisión de casos (Semana 3, módulo Juan José).

`GET /cases/{caseId}` devuelve el caso con su explicación legible y su traza de
auditoría. La lectura se resuelve por el puerto `CaseReadRepository` (PostgreSQL
en producción, memoria en dev/test). Responde 404 (CASE_NOT_FOUND) si no existe.

Pendiente de seguridad (Lucas): proteger el endpoint con `require_roles(...)`
(lectura para Analista/Auditor/Administrador) y el acceso temporal a documentos.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.application.dtos.explanation_dto import serialize_explanation
from app.domain.exceptions.case_exceptions import CaseNotFoundError
from app.domain.repositories.case_read_repository import CaseDetail, CaseReadRepository
from app.presentation.api.dependencies.cases import get_case_read_repository
from app.presentation.schemas.case_schema import CaseDetailResponse, ExplanationSchema

router = APIRouter(prefix="/cases", tags=["cases"])


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
) -> CaseDetailResponse:
    detail = repo.get_case(case_id)
    if detail is None:
        raise CaseNotFoundError(case_id)
    return _to_response(detail)
