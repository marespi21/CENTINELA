"""Composition root de la lectura de casos (Semana 3, módulo Juan José).

Con la base de casos configurada (`CASES_DB_DSN`) → adaptador PostgreSQL;
sin configuración → en memoria (dev/test). La API depende solo del puerto.
"""

from __future__ import annotations

from functools import lru_cache

from app.domain.repositories.case_read_repository import CaseReadRepository
from app.infrastructure.config.settings import settings
from app.infrastructure.repositories.in_memory_case_read_repository import (
    InMemoryCaseReadRepository,
)


@lru_cache(maxsize=1)
def get_case_read_repository() -> CaseReadRepository:
    if settings.cases_db_configured:
        from app.infrastructure.postgres.pg_case_read_repository import (
            PgCaseReadRepository,
        )

        return PgCaseReadRepository(dsn=settings.cases_db_dsn)
    return InMemoryCaseReadRepository()
