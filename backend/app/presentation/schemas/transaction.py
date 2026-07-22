from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class LocationSchema(BaseModel):
    latitude: float = Field(..., description="Latitude in degrees")
    longitude: float = Field(..., description="Longitude in degrees")

    model_config = ConfigDict(extra="forbid")

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if v < -90 or v > 90:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if v < -180 or v > 180:
            raise ValueError("longitude must be between -180 and 180")
        return v


CurrencyCode = Literal["COP"]


class TransactionInSchema(BaseModel):
    """Schema de entrada para ingesta de transacciones (Semana 1).

    Seguridad/robustez:
    - Rechaza campos extra.
    - Valida rangos y tipos.
    """

    transactionId: UUID
    accountId: str = Field(..., min_length=1, max_length=64)
    amount: float = Field(..., gt=0, description="Amount must be > 0")
    currency: CurrencyCode
    merchantId: str = Field(..., min_length=1, max_length=64)
    merchantCategory: str = Field(..., min_length=1, max_length=64)
    timestamp: datetime
    location: LocationSchema

    model_config = ConfigDict(extra="forbid")

    @field_validator("accountId")
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        # Evita strings peligrosas por longitud/carácter. Ajustable en semanas futuras.
        if "\n" in v or "\r" in v:
            raise ValueError("accountId must not contain newlines")
        return v

    @field_validator("merchantId")
    @classmethod
    def validate_merchant_id(cls, v: str) -> str:
        if "\n" in v or "\r" in v:
            raise ValueError("merchantId must not contain newlines")
        return v

    @model_validator(mode="after")
    def validate_timestamp_not_far_future(self) -> "TransactionInSchema":
        # Evita payloads absurdos y reduce riesgo de inconsistencias.
        # Permitimos hasta 2 horas en el futuro.
        now = datetime.now(tz=self.timestamp.tzinfo) if self.timestamp.tzinfo else datetime.now()
        if self.timestamp > now:
            # Si el timezone es distinto, la comparación seguirá siendo válida por Python.
            max_future_seconds = 2 * 60 * 60
            if (self.timestamp - now).total_seconds() > max_future_seconds:
                raise ValueError("timestamp is too far in the future")
        return self

