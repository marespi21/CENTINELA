"""Schema de respuesta del acceso temporal a un documento (Semana 3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentAccessResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    url: str
    expires_at: datetime = Field(alias="expiresAt", serialization_alias="expiresAt")
