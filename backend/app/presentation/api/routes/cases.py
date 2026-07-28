"""API de revisión y gestión de casos (Semana 3 y 5).

Semana 3 (lectura):
- `GET /cases/{caseId}` devuelve el caso con su explicación legible y su traza.
- `GET /cases/{caseId}/documents/{blobName}` entrega una URL temporal (SAS).

Semana 5 (bandeja y acciones de la consola):
- `GET /cases` lista los casos con filtros y paginación (bandeja).
- `POST /cases/{caseId}/assign` asigna el caso a un analista.
- `POST /cases/{caseId}/resolve` marca el caso como resuelto.

Lectura: rol Analista, Auditor o Administrador. Acciones (assign/resolve): rol
Analista o Administrador. 401 sin clave, 403 con rol no autorizado. Con
AUTH_ENABLED=false (local) no bloquean.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.application.dtos.explanation_dto import serialize_explanation
from app.application.use_cases.assign_case import AssignCaseUseCase
from app.application.use_cases.list_cases import ListCasesUseCase
from app.application.use_cases.resolve_case import ResolveCaseUseCase
from app.domain.exceptions.case_exceptions import CaseNotFoundError
from app.domain.repositories.case_document_repository import CaseDocumentRepository
from app.domain.repositories.case_read_repository import (
    CaseDetail,
    CasePage,
    CaseReadRepository,
    CaseSummary,
)
from app.domain.repositories.case_write_repository import CaseWriteRepository
from app.domain.repositories.document_access_provider import DocumentAccessProvider
from app.domain.value_objects.role import Role
from app.presentation.api.dependencies.cases import (
    get_case_document_repository,
    get_case_read_repository,
    get_case_write_repository,
)
from app.presentation.api.dependencies.document_access import (
    get_document_access_provider,
)
from app.presentation.api.dependencies.security import Principal, require_roles
from app.presentation.schemas.case_schema import (
    AssignCaseRequest,
    CaseDetailResponse,
    CaseDocumentListResponse,
    CaseDocumentResponse,
    CaseListResponse,
    CaseSummaryResponse,
    ExplanationSchema,
    ResolveCaseRequest,
)
from app.presentation.schemas.document_access_schema import DocumentAccessResponse

router = APIRouter(prefix="/cases", tags=["cases"])

# Lectura de casos: analista, auditor o administrador.
_read_case = require_roles(Role.ANALISTA, Role.AUDITOR, Role.ADMINISTRADOR)
# Acciones sobre casos: analista o administrador (el auditor es solo lectura).
_act_case = require_roles(Role.ANALISTA, Role.ADMINISTRADOR)


def _to_response(detail: CaseDetail) -> CaseDetailResponse:
    return CaseDetailResponse(
        case_id=detail.case_id,
        transaction_id=detail.transaction_id,
        account_id=detail.account_id,
        status=detail.status,
        opened_at=detail.opened_at,
        assigned_to=detail.assignee,
        explanation=ExplanationSchema.model_validate(
            serialize_explanation(detail.explanation)
        ),
        audit_trail=detail.audit_trail,
    )


def _to_summary_response(summary: CaseSummary) -> CaseSummaryResponse:
    return CaseSummaryResponse(
        case_id=summary.case_id,
        transaction_id=summary.transaction_id,
        account_id=summary.account_id,
        status=summary.status,
        opened_at=summary.opened_at,
        score=summary.score,
        is_case=summary.is_case,
        summary=summary.summary,
        assigned_to=summary.assignee,
    )


def _to_list_response(page: CasePage) -> CaseListResponse:
    return CaseListResponse(
        items=[_to_summary_response(s) for s in page.items],
        total=page.total,
        page=page.page,
        page_size=page.page_size,
    )


@router.get(
    "",
    response_model=CaseListResponse,
    summary="Bandeja de casos con filtros y paginación (Semana 5)",
)
async def list_cases(
    status: str | None = Query(default=None, description="Estado del caso"),
    assigned_to: str | None = Query(default=None, alias="assignedTo"),
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    repo: CaseReadRepository = Depends(get_case_read_repository),
    _principal: Principal = Depends(_read_case),
) -> CaseListResponse:
    result = ListCasesUseCase(repo).execute(
        status=status,
        assigned_to=assigned_to,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return _to_list_response(result)


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


@router.post(
    "/{case_id}/assign",
    response_model=CaseDetailResponse,
    summary="Asignar el caso a un analista (Semana 5)",
)
async def assign_case(
    case_id: str,
    body: AssignCaseRequest,
    read: CaseReadRepository = Depends(get_case_read_repository),
    write: CaseWriteRepository = Depends(get_case_write_repository),
    principal: Principal = Depends(_act_case),
) -> CaseDetailResponse:
    actor = principal.role.value
    assignee = body.assignee_id or principal.api_key or actor
    detail = AssignCaseUseCase(write, read).execute(
        case_id, assignee=assignee, actor=actor
    )
    return _to_response(detail)


@router.post(
    "/{case_id}/resolve",
    response_model=CaseDetailResponse,
    summary="Marcar el caso como resuelto (Semana 5)",
)
async def resolve_case(
    case_id: str,
    body: ResolveCaseRequest,
    read: CaseReadRepository = Depends(get_case_read_repository),
    write: CaseWriteRepository = Depends(get_case_write_repository),
    principal: Principal = Depends(_act_case),
) -> CaseDetailResponse:
    actor = principal.role.value
    detail = ResolveCaseUseCase(write, read).execute(
        case_id, resolution=body.resolution, note=body.note, actor=actor
    )
    return _to_response(detail)


@router.get(
    "/{case_id}/documents",
    response_model=CaseDocumentListResponse,
    summary="Documentos del caso con URL temporal (SAS) (Semana 5)",
)
async def list_case_documents(
    case_id: str,
    documents: CaseDocumentRepository = Depends(get_case_document_repository),
    provider: DocumentAccessProvider = Depends(get_document_access_provider),
    _principal: Principal = Depends(_read_case),
) -> CaseDocumentListResponse:
    items = []
    for doc in documents.list_for_case(case_id):
        access = provider.temporary_read_url(doc.blob_name)
        items.append(
            CaseDocumentResponse(
                blob_name=doc.blob_name,
                filename=doc.filename,
                content_type=doc.content_type,
                url=access.url,
                expires_at=access.expires_at,
            )
        )
    return CaseDocumentListResponse(items=items)


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
