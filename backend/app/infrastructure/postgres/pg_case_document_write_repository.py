"""Escritura del índice de documentos sobre PostgreSQL (Sprint 6, Fase 2).

Escribe en `caso_documentos`, la tabla que hasta ahora solo se leía. Guarda
junto a la referencia del blob el veredicto del contraste con la transacción.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.domain.entities.document_verification import DocumentVerification
from app.domain.repositories.case_document_write_repository import (
    CaseDocumentWriteRepository,
)


class PgCaseDocumentWriteRepository(CaseDocumentWriteRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def save_document(
        self,
        case_id: str,
        blob_name: str,
        filename: str,
        content_type: str,
        uploaded_at: datetime,
        verification: DocumentVerification | None = None,
    ) -> None:
        import psycopg

        verdict = verification.verdict.value if verification else None
        summary = verification.summary if verification else None
        detail = (
            json.dumps(
                [
                    {
                        "campo": c.field_name,
                        "documento": c.document_value,
                        "transaccion": c.transaction_value,
                        "coincide": c.matches,
                        "detalle": c.detail,
                    }
                    for c in verification.comparisons
                ]
            )
            if verification
            else None
        )
        verified_at = datetime.now(timezone.utc) if verification else None

        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            # ON CONFLICT sobre (caso_id, blob_name), que ya tenía UNIQUE: la
            # cola entrega "al menos una vez", así que reprocesar un mensaje
            # tiene que actualizar el veredicto, no reventar por clave duplicada
            # ni duplicar la fila.
            cur.execute(
                """
                INSERT INTO caso_documentos (
                    caso_id, blob_name, filename, content_type, subido_en,
                    veredicto, verificacion_resumen, verificacion_detalle,
                    verificado_en
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (caso_id, blob_name) DO UPDATE SET
                    filename = EXCLUDED.filename,
                    content_type = EXCLUDED.content_type,
                    veredicto = EXCLUDED.veredicto,
                    verificacion_resumen = EXCLUDED.verificacion_resumen,
                    verificacion_detalle = EXCLUDED.verificacion_detalle,
                    verificado_en = EXCLUDED.verificado_en
                """,
                (
                    case_id,
                    blob_name,
                    filename,
                    content_type,
                    uploaded_at,
                    verdict,
                    summary,
                    detail,
                    verified_at,
                ),
            )
            conn.commit()
