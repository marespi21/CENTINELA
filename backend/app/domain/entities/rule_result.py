from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuleResult:
    """Resultado de evaluar UNA regla de fraude sobre una transacción.

    `observed` guarda los valores CONCRETOS que llevaron a la decisión
    (no solo el id de la regla): p. ej. el monto observado y el promedio de
    la cuenta, la velocidad implícita en km/h, el conteo en la ventana, etc.
    Ese detalle es el que se persiste como evidencia de activación.
    """

    rule_id: str
    triggered: bool
    points: int
    observed: dict[str, Any] = field(default_factory=dict)
