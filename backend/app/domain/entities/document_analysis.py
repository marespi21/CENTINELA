"""Resultado de extraer datos de un comprobante (Sprint 6, Fase 2).

Es lo que devuelve el OCR: los campos que se pudieron leer del documento, cada
uno con la confianza que el modelo les asigna. No juzga nada — comparar contra
la transacción es trabajo de `DocumentVerifier`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ExtractedField:
    """Un campo leído del documento y cuánto se fía el modelo de esa lectura.

    `confidence` va de 0.0 a 1.0. Se conserva porque una lectura con confianza
    baja no debe tratarse igual que una nítida: ver `DocumentVerifier`.
    """

    value: str
    confidence: float


@dataclass(frozen=True)
class DocumentAnalysis:
    """Campos extraídos de un comprobante.

    Todos los campos son opcionales a propósito: un comprobante arrugado, una
    foto borrosa o un PDF escaneado del revés puede dar cero, uno o todos. El
    caso "no se pudo leer nada" es normal y hay que representarlo, no tratarlo
    como error.
    """

    total: Decimal | None = None
    total_confidence: float = 0.0
    transaction_date: datetime | None = None
    date_confidence: float = 0.0
    merchant_name: ExtractedField | None = None
    currency: str | None = None
    # Texto plano completo, por si el analista quiere leerlo en la consola.
    raw_text: str = ""
    # Modelo del servicio que produjo la extracción (prebuilt-receipt, etc.).
    model_id: str = ""
    fields: dict[str, ExtractedField] = field(default_factory=dict)

    @property
    def is_empty(self) -> bool:
        """True si el OCR no logró sacar ningún dato contrastable."""
        return (
            self.total is None
            and self.transaction_date is None
            and self.merchant_name is None
        )
