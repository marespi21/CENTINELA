"""Tests del contraste comprobante ↔ transacción (Sprint 6, Fase 2).

Servicio de dominio puro: se prueba entero sin Azure, sin OCR y sin base de
datos. Es donde vive la decisión que el analista va a leer, así que es lo que
más falta hace tener clavado.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.domain.entities.document_analysis import DocumentAnalysis, ExtractedField
from app.domain.entities.document_verification import VerificationVerdict
from app.domain.entities.transaction import Transaction
from app.domain.services.document_verifier import DocumentVerifier
from app.domain.value_objects.verification_config import VerificationConfig

TX_TIME = datetime(2026, 7, 20, 15, 30, tzinfo=timezone.utc)


def _transaction(amount: str = "250000", merchant_id: str = "m1") -> Transaction:
    return Transaction(
        transaction_id=uuid4(),
        account_id="acc-1",
        amount=Decimal(amount),
        currency="COP",
        merchant_id=merchant_id,
        merchant_category="retail",
        timestamp=TX_TIME,
        latitude=Decimal("4.7110"),
        longitude=Decimal("-74.0721"),
    )


def _analysis(**kwargs: object) -> DocumentAnalysis:
    defaults: dict[str, object] = {
        "total": Decimal("250000"),
        "total_confidence": 0.95,
        "transaction_date": TX_TIME,
        "date_confidence": 0.95,
    }
    defaults.update(kwargs)
    return DocumentAnalysis(**defaults)  # type: ignore[arg-type]


class TestVeredictos:
    def test_comprobante_que_respalda_la_transaccion(self) -> None:
        result = DocumentVerifier().verify(_analysis(), _transaction())

        assert result.verdict is VerificationVerdict.COINCIDE
        assert not result.is_suspicious

    def test_importe_distinto_marca_discrepancia(self) -> None:
        """El caso que justifica toda la fase: el papel no cuadra con el cargo."""
        analysis = _analysis(total=Decimal("50000"))

        result = DocumentVerifier().verify(analysis, _transaction("250000"))

        assert result.verdict is VerificationVerdict.DISCREPA
        assert result.is_suspicious
        assert "importe" in result.summary

    def test_fecha_fuera_de_ventana_marca_discrepancia(self) -> None:
        analysis = _analysis(transaction_date=TX_TIME + timedelta(days=10))

        result = DocumentVerifier().verify(analysis, _transaction())

        assert result.verdict is VerificationVerdict.DISCREPA
        assert "fecha" in result.summary

    def test_documento_sin_datos_es_ilegible(self) -> None:
        result = DocumentVerifier().verify(DocumentAnalysis(), _transaction())

        assert result.verdict is VerificationVerdict.ILEGIBLE

    def test_lectura_poco_fiable_no_acusa_de_fraude(self) -> None:
        """Un OCR inseguro no puede producir DISCREPA.

        Con confianza por debajo del umbral el campo se descarta: es preferible
        decir 'no sé' a acusar a un cliente por una cifra mal reconocida.
        """
        analysis = _analysis(
            total=Decimal("999"), total_confidence=0.20,
            transaction_date=None, date_confidence=0.0,
            merchant_name=ExtractedField(value="Tienda", confidence=0.1),
        )

        result = DocumentVerifier().verify(analysis, _transaction("250000"))

        assert result.verdict is VerificationVerdict.INSUFICIENTE


class TestTolerancias:
    def test_diferencia_pequena_se_admite(self) -> None:
        """1 % de diferencia entra en la tolerancia del 2 %."""
        analysis = _analysis(total=Decimal("252500"))

        result = DocumentVerifier().verify(analysis, _transaction("250000"))

        assert result.verdict is VerificationVerdict.COINCIDE

    def test_tolerancia_absoluta_protege_importes_pequenos(self) -> None:
        """En importes bajos el 2 % es ruido; manda la tolerancia absoluta."""
        analysis = _analysis(total=Decimal("5500"))

        result = DocumentVerifier().verify(analysis, _transaction("5000"))

        assert result.verdict is VerificationVerdict.COINCIDE

    def test_la_configuracion_endurece_el_criterio(self) -> None:
        estricta = VerificationConfig(
            amount_tolerance_ratio=Decimal("0"),
            amount_tolerance_absolute=Decimal("0"),
            date_window_days=0,
        )
        analysis = _analysis(total=Decimal("250001"))

        result = DocumentVerifier(estricta).verify(analysis, _transaction("250000"))

        assert result.verdict is VerificationVerdict.DISCREPA

    def test_fecha_dentro_de_la_ventana_se_admite(self) -> None:
        """El comercio puede liquidar con retraso: 2 días no es discrepancia."""
        analysis = _analysis(transaction_date=TX_TIME + timedelta(days=2))

        result = DocumentVerifier().verify(analysis, _transaction())

        assert result.verdict is VerificationVerdict.COINCIDE


class TestComercio:
    def test_el_comercio_solo_no_dicta_el_veredicto(self) -> None:
        """`merchant_id` es un identificador opaco, no un nombre comercial.

        Si decidiera, cualquier ticket de una tienda real discreparía de `m1` y
        el sistema gritaría fraude en todas partes.
        """
        analysis = _analysis(
            merchant_name=ExtractedField(value="Supermercado Los Andes", confidence=0.9)
        )

        result = DocumentVerifier().verify(analysis, _transaction(merchant_id="m1"))

        assert result.verdict is VerificationVerdict.COINCIDE
        comercio = [c for c in result.comparisons if c.field_name == "comercio"]
        assert comercio and not comercio[0].matches

    def test_el_desglose_acompana_al_veredicto(self) -> None:
        """Un 'discrepa' sin justificación no es accionable para el analista."""
        result = DocumentVerifier().verify(
            _analysis(total=Decimal("1")), _transaction("250000")
        )

        importe = [c for c in result.comparisons if c.field_name == "importe"]
        assert importe
        assert importe[0].document_value == "1"
        assert importe[0].transaction_value == "250000"
        assert importe[0].detail


class TestZonaHoraria:
    def test_fecha_sin_huso_no_revienta(self) -> None:
        """El OCR devuelve fechas naive; la transacción las tiene con huso."""
        analysis = _analysis(transaction_date=datetime(2026, 7, 20, 15, 30))

        result = DocumentVerifier().verify(analysis, _transaction())

        assert result.verdict is VerificationVerdict.COINCIDE
