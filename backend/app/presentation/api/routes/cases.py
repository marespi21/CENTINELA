"""API de revisión de casos (Semana 3) — STUB de contrato.

Este archivo fija la RUTA y el CONTRATO de salida para desbloquear al equipo.
Está deliberadamente sin implementar (501) para que:

- Gestión de casos (Juanjose) inyecte un `CaseReadRepository` y mapee
  `CaseDetail` -> `CaseDetailResponse` (ver TODO).
- Seguridad (Lucas) proteja el endpoint con `require_roles(...)` (lectura para
  Analista/Auditor/Administrador) y resuelva el acceso temporal a documentos.

No cambiar la forma de `CaseDetailResponse` sin acordarlo: la consumen la API,
la mensajería y el frontend.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.presentation.schemas.case_schema import CaseDetailResponse

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get(
    "/{case_id}",
    response_model=CaseDetailResponse,
    summary="Detalle de un caso con su explicación (Semana 3)",
)
async def get_case(case_id: str) -> CaseDetailResponse:
    # TODO(Juanjose): inyectar CaseReadRepository, buscar el caso y mapearlo;
    #   devolver 404 (CASE_NOT_FOUND) si no existe.
    # TODO(Lucas): añadir Depends(require_roles(...)) para lectura de casos.
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "detail": "Case review endpoint not implemented yet (contract stub).",
            "code": "NOT_IMPLEMENTED",
            "caseId": case_id,
        },
    )
