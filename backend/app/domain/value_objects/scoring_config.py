from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class ScoringConfig:
    """Parámetros del motor de scoring.

    Es un objeto de dominio inmutable. La capa externa (settings / app
    settings de la función) lo construye a partir de configuración externa,
    de modo que el UMBRAL y los pesos se puedan cambiar SIN redespliegue.
    """

    # Umbral: score >= threshold ⇒ se abre un caso.
    threshold: int = 50

    # Pesos (puntos) por regla.
    weight_velocity: int = 25
    weight_atypical_amount: int = 30
    weight_geo_impossible: int = 45
    weight_risky_merchant: int = 20

    # Regla velocidad: N o más transacciones en una ventana de M minutos.
    velocity_max_tx: int = 5
    velocity_window_minutes: int = 10

    # Regla monto atípico: monto > factor * promedio de la cuenta.
    # Si el historial tiene menos de `amount_min_history`, se usa el tope absoluto.
    amount_factor: Decimal = Decimal("3.0")
    amount_min_history: int = 3
    amount_absolute_cap: Decimal = Decimal(1000000)

    # Regla geo-imposible: velocidad implícita entre dos transacciones > tope.
    geo_max_speed_kmh: Decimal = Decimal(900)

    # Regla comercio de riesgo: categoría del comercio en el conjunto de riesgo.
    risky_categories: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"gambling", "crypto", "wire_transfer", "gift_cards", "adult"}
        )
    )
