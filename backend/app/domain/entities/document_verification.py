"""Veredicto de contrastar un comprobante contra la transacción del caso.

El objetivo del Sprint 6 Fase 2 no es "leer papeles", es darle al analista una
señal accionable: ¿este comprobante respalda la transacción que disparó el caso,
o la contradice?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VerificationVerdict(str, Enum):
    """Resultado del contraste. Hereda de str para serializar directo a JSON."""

    # Todo lo contrastable coincide con la transacción.
    COINCIDE = "coincide"
    # Al menos un campo contradice la transacción: es la señal de fraude.
    DISCREPA = "discrepa"
    # Se leyó algo, pero no lo suficiente para afirmar ni desmentir.
    INSUFICIENTE = "insuficiente"
    # El OCR no pudo extraer ningún dato utilizable.
    ILEGIBLE = "ilegible"


@dataclass(frozen=True)
class FieldComparison:
    """Comparación de un campo concreto: qué decía el documento y qué la transacción."""

    field_name: str
    document_value: str
    transaction_value: str
    matches: bool
    # Por qué coincide o no, en lenguaje que el analista pueda leer.
    detail: str = ""


@dataclass(frozen=True)
class DocumentVerification:
    """Veredicto completo, con el detalle que lo sostiene.

    Se guarda el desglose además del veredicto porque un analista que ve
    "discrepa" necesita saber *en qué* discrepa para decidir; un veredicto sin
    justificación no es accionable.
    """

    verdict: VerificationVerdict
    comparisons: list[FieldComparison] = field(default_factory=list)
    summary: str = ""

    @property
    def is_suspicious(self) -> bool:
        """True si el documento contradice la transacción."""
        return self.verdict is VerificationVerdict.DISCREPA
