"""Puerto de análisis documental (OCR) — Sprint 6, Fase 2.

El dominio no sabe que detrás hay Azure Document Intelligence: solo pide que
alguien convierta unos bytes en `DocumentAnalysis`. Eso permite verificar toda
la lógica de contraste con un doble en memoria, sin gastar página alguna de la
capa gratuita.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.document_analysis import DocumentAnalysis


class DocumentAnalysisError(Exception):
    """El servicio de OCR no pudo procesar el documento.

    Se distingue de "documento ilegible": esto es un fallo del servicio (caído,
    cuota agotada, formato rechazado) y el mensaje debe reintentarse, mientras
    que un documento ilegible es un resultado legítimo que no hay que reintentar.
    """


class DocumentAnalyzer(ABC):
    @abstractmethod
    def analyze(self, content: bytes, content_type: str) -> DocumentAnalysis:
        """Extrae los campos del comprobante.

        Devuelve un `DocumentAnalysis` vacío si el documento es ilegible.
        Lanza `DocumentAnalysisError` si el fallo es del servicio.
        """
        raise NotImplementedError
