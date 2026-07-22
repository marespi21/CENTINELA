import pytest
from uuid import uuid4
from datetime import datetime, timezone

from backend.app.presentation.schemas.transaction import TransactionInSchema


def make_payload(**overrides):
    payload = {
        "transactionId": uuid4(),
        "accountId": "acc_123",
        "amount": 50000.0,
        "currency": "COP",
        "merchantId": "MERCHANT001",
        "merchantCategory": "SUPERMARKET",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": {"latitude": 6.2442, "longitude": -75.5812},
    }
    payload.update(overrides)
    return payload


def test_schema_accepts_valid_payload():
    schema = TransactionInSchema(**make_payload())
    assert schema.transactionId
    assert schema.location.latitude == 6.2442


def test_schema_rejects_extra_fields():
    with pytest.raises(Exception):
        TransactionInSchema(**{**make_payload(), "evil": "x"})


def test_schema_rejects_invalid_latitude():
    with pytest.raises(Exception):
        TransactionInSchema(**make_payload(location={"latitude": 100.0, "longitude": 0.0}))


def test_schema_rejects_negative_amount():
    with pytest.raises(Exception):
        TransactionInSchema(**make_payload(amount=-1.0))


def test_schema_rejects_invalid_uuid():
    with pytest.raises(Exception):
        TransactionInSchema(**make_payload(transactionId="not-a-uuid"))

