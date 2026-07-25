"""Explicación legible de una decisión de scoring (Semana 3 — explicador).

Es el objeto de dominio que responde "¿por qué se abrió (o no) este caso?" en
lenguaje que un analista entiende, sin exponer la mecánica interna del motor.
Se construye a partir de un `ScoringResult` mediante un `Explainer`.

Este módulo es CONTRATO COMPARTIDO del sprint: la mensajería lo publica en la
cola de casos, el almacén de casos lo persiste y la API lo devuelve. No cambiar
sus campos sin acordar con mensajería y gestión de casos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ExplanationReason:
    """Una razón concreta de la decisión: la regla que se activó y su evidencia.

    - `title`/`description`: texto legible tomado del catálogo de reglas.
    - `detail`: frase con los valores observados que dispararon la regla.
    - `observed`: evidencia cruda (los mismos valores del `RuleResult`).
    """

    rule_id: str
    title: str
    description: str
    detail: str
    points: int
    observed: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Explanation:
    """Explicación estructurada de la decisión de scoring de una transacción."""

    transaction_id: UUID
    account_id: str
    score: int
    threshold: int
    is_case: bool
    summary: str
    reasons: list[ExplanationReason]
    generated_at: datetime
