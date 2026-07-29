"""Escritura append-only de explicaciones sobre PostgreSQL (Sprint 6, Fase 4)."""

from __future__ import annotations

from app.application.dtos.explanation_dto import serialize_explanation
from app.domain.entities.explanation import Explanation
from app.domain.repositories.case_explanation_repository import (
    CaseExplanationRepository,
)


class PgCaseExplanationRepository(CaseExplanationRepository):
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def append_explanation(self, case_id: str, explanation: Explanation) -> None:
        import psycopg
        from psycopg.types.json import Jsonb

        with psycopg.connect(self._dsn) as conn, conn.cursor() as cur:
            # INSERT y no UPDATE: la tabla es append-only y auditada, y la
            # lectura toma la fila más reciente (ORDER BY creado_en DESC LIMIT 1).
            # Así la explicación por reglas queda como traza de lo que se dijo
            # primero, y el enriquecimiento pasa a mostrarse solo.
            cur.execute(
                """
                INSERT INTO caso_explicaciones
                    (caso_id, transaction_id, account_id, score, threshold,
                     is_case, summary, explanation, generado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    case_id,
                    str(explanation.transaction_id),
                    explanation.account_id,
                    explanation.score,
                    explanation.threshold,
                    explanation.is_case,
                    explanation.summary,
                    Jsonb(serialize_explanation(explanation)),
                    explanation.generated_at,
                ),
            )
            conn.commit()
