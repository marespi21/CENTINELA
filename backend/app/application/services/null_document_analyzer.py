"""Analizador nulo: el sistema funciona sin OCR configurado (Sprint 6, Fase 2).

Sin `DOC_INTELLIGENCE_ENDPOINT` no hay a quién preguntar, pero eso no puede
tumbar el worker ni bloquear la cola `documents`. Este adaptador devuelve una
extracción vacía, con lo que el verificador emite ILEGIBLE y el documento queda
igualmente vinculado al caso. Es el mismo criterio que el resto del sistema
aplica con Cosmos o PostgreSQL: sin configuración, adaptador degradado, nunca
un arranque fallido.
"""

from __future__ import annotations

import logging

from app.domain.entities.document_analysis import DocumentAnalysis
from app.domain.repositories.document_analyzer import DocumentAnalyzer

logger = logging.getLogger(__name__)


class NullDocumentAnalyzer(DocumentAnalyzer):
    def analyze(self, content: bytes, content_type: str) -> DocumentAnalysis:
        logger.info(
            "OCR no configurado (falta DOC_INTELLIGENCE_ENDPOINT); "
            "el documento de %s bytes se registra sin extracción",
            len(content),
        )
        return DocumentAnalysis(model_id="none")
