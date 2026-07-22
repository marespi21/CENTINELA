from uuid import uuid4
from datetime import datetime, timezone

import pytest
import httpx

from backend.app.main import app


def make_payload():
    return {
        "transactionId": str(uuid4()),
        "accountId": "acc_123",
        "amount": 50000.0,
        "currency": "COP",
        "merchantId": "MERCHANT001",
        "merchantCategory": "SUPERMARKET",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": {"latitude": 6.2442, "longitude": -75.5812},
    }


@pytest.mark.asyncio
async def test_post_transactions_returns_202_and_ack():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post("/api/v1/transactions", json=make_payload())

    assert resp.status_code == 202
    data = resp.json()
    assert data["accepted"] is True
    assert "transactionId" in data


@pytest.mark.asyncio
async def test_post_transactions_invalid_payload_returns_400():
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/transactions",
            json={**make_payload(), "amount": -1},
        )

    assert resp.status_code == 400
    data = resp.json()
    assert data["code"] == "BAD_REQUEST"
    assert "detail" in data

