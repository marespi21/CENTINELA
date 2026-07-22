from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.application.dtos.document_dto import UploadDocumentInput
from app.application.use_cases.upload_document import UploadDocumentUseCase
from app.domain.value_objects.role import Role
from app.presentation.api.dependencies.documents import (
    get_upload_document_use_case,
)
from app.presentation.api.dependencies.security import Principal, require_roles
from app.presentation.schemas.document_schema import DocumentAcceptedResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Subir un documento",
    description=(
        "Recibe un archivo (multipart/form-data), lo almacena en Blob Storage "
        "y publica un evento en la Queue para procesamiento posterior."
    ),
)
async def upload_document(
    file: UploadFile = File(...),
    use_case: UploadDocumentUseCase = Depends(get_upload_document_use_case),
    _principal: Principal = Depends(
        require_roles(Role.SERVICIO, Role.ADMINISTRADOR)
    ),
) -> DocumentAcceptedResponse:
    content = await file.read()
    result = use_case.execute(
        UploadDocumentInput(
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            content=content,
        )
    )
    return DocumentAcceptedResponse(
        document_id=result.document_id,
        blob_name=result.blob_name,
        status=result.status,
    )
