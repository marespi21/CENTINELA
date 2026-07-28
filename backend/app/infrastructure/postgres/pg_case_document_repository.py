"""Índice de documentos de casos sobre PostgreSQL (Semana 5).

Lee la tabla `caso_documentos` (ver scripts/init-cases-db.sql), que vincula cada
caso con los blobs de sus documentos de verificación. El SDK (`psycopg`) se
importa de forma perezosa; en dev/test se usa el adaptador en memoria.
"""

from __future__ import annotations

from typing import Any

from app.domain.repositories.case_document_repository import (
    CaseDocument,
    CaseDocumentRepository,
)


def build_case_document(row: tuple[Any, ...]) -> CaseDocument:
    """Fila de `caso_documentos` → `CaseDocument` (función pura, testeable)."""
    return CaseDocument(
        blob_name=str(row[0]),
        filename=str(row[1]) if row[1] else "",
        content_type=str(row[2]) if row[2] else "application/octet-stream",
        uploaded_at=row[3],
    )


class PgCaseDocumentRepository(CaseDocumentRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def list_for_case(self, case_id: str) -> list[CaseDocument]:
        import psycopg

        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT blob_name, filename, content_type, subido_en
                FROM caso_documentos
                WHERE caso_id = %s
                ORDER BY subido_en DESC
                """,
                (case_id,),
            )
            return [build_case_document(row) for row in cur.fetchall()]
