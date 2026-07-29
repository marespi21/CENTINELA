"""Parámetros del contraste documento ↔ transacción (Sprint 6, Fase 2).

Igual que `ScoringConfig`, se lee del entorno: afinar la tolerancia no exige
reconstruir la imagen ni tocar código.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class VerificationConfig:
    """Umbrales del verificador documental."""

    # Diferencia relativa admitida entre el total del comprobante y el importe
    # de la transacción. Un 2 % absorbe redondeos, propinas e IVA prorrateado
    # sin dejar pasar discrepancias reales.
    amount_tolerance_ratio: Decimal = Decimal("0.02")
    # Diferencia absoluta admitida siempre, para importes pequeños donde el
    # porcentaje se queda corto (2 % de 1000 COP es ruido).
    amount_tolerance_absolute: Decimal = Decimal("1000")
    # Ventana de días entre la fecha del comprobante y la de la transacción.
    # El comercio puede liquidar con retraso, así que exigir el mismo día
    # generaría falsos positivos.
    date_window_days: int = 3
    # Por debajo de esta confianza, la lectura del OCR NO se usa para juzgar:
    # no cuenta ni a favor ni en contra. Un campo mal leído no puede acusar de
    # fraude a nadie.
    min_field_confidence: float = 0.60
