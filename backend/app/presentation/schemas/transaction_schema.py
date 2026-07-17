from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreateRequest(BaseModel):
    """Contrato HTTP de entrada para POST /transactions.

    timestamp lo genera el servidor en el caso de uso (UTC).
    """

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "transactionId": "550e8400-e29b-41d4-a716-446655440000",
                "accountId": "acc-001",
                "amount": "150000.50",
                "currency": "COP",
                "merchantId": "mer-9",
                "merchantCategory": "restaurants",
                "latitude": "4.7110",
                "longitude": "-74.0721",
            }
        },
    )

    transaction_id: UUID = Field(alias="transactionId")
    account_id: str = Field(alias="accountId", min_length=1)
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    merchant_id: str = Field(alias="merchantId", min_length=1)
    merchant_category: str = Field(alias="merchantCategory", min_length=1)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)


class TransactionAcceptedResponse(BaseModel):
    """Respuesta 202 Accepted."""

    model_config = ConfigDict(populate_by_name=True)

    transaction_id: UUID = Field(alias="transactionId", serialization_alias="transactionId")
    status: str = "accepted"
