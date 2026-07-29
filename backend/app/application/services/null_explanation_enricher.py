"""Enriquecedor nulo: el sistema funciona sin servicio de enriquecimiento.

Mientras no haya un servicio configurado, devuelve None y el caso conserva su
explicación por reglas. Mismo criterio que `NullDocumentAnalyzer`: sin
configuración, adaptador degradado, nunca un arranque fallido.

Es también lo que hace que toda la tubería asíncrona —cola, consumidor,
persistencia append-only— se pueda probar y desplegar antes de decidir qué
servicio redactará la narrativa.
"""

from __future__ import annotations

import logging

from app.domain.entities.explanation import Explanation
from app.domain.services.explanation_enricher import (
    EnrichmentContext,
    ExplanationEnricher,
)

logger = logging.getLogger(__name__)


class NullExplanationEnricher(ExplanationEnricher):
    def enrich(self, context: EnrichmentContext) -> Explanation | None:
        logger.debug(
            "enriquecedor no configurado; el caso %s conserva su explicación por reglas",
            context.case_id,
        )
        return None
