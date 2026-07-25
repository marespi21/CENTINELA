"""Catálogo legible de las reglas de fraude (para el explicador, Semana 3).

Mapea el `rule_id` estable (persistido en el detalle del scoring) a un título y
una descripción en lenguaje humano. Es la fuente única de verdad de las etiquetas
que ve un analista; el motor de reglas sigue usando solo los `rule_id`.
"""

from __future__ import annotations

from app.domain.services.rules import (
    RULE_ATYPICAL_AMOUNT,
    RULE_GEO_IMPOSSIBLE,
    RULE_RISKY_MERCHANT,
    RULE_VELOCITY,
)

# rule_id -> (título legible, descripción corta)
RULE_CATALOG: dict[str, tuple[str, str]] = {
    RULE_VELOCITY: (
        "Velocidad de transacciones inusual",
        "La cuenta realizó demasiadas transacciones en una ventana corta.",
    ),
    RULE_ATYPICAL_AMOUNT: (
        "Monto atípico",
        "El monto supera de forma notable lo habitual de la cuenta.",
    ),
    RULE_GEO_IMPOSSIBLE: (
        "Desplazamiento geográfico imposible",
        "La distancia respecto a la transacción anterior implica una velocidad "
        "físicamente imposible.",
    ),
    RULE_RISKY_MERCHANT: (
        "Comercio de categoría de riesgo",
        "La categoría del comercio está marcada como de riesgo.",
    ),
}


def rule_title(rule_id: str) -> str:
    """Título legible de la regla; cae al propio id si no está catalogada."""
    entry = RULE_CATALOG.get(rule_id)
    return entry[0] if entry else rule_id


def rule_description(rule_id: str) -> str:
    """Descripción corta de la regla; vacía si no está catalogada."""
    entry = RULE_CATALOG.get(rule_id)
    return entry[1] if entry else ""
