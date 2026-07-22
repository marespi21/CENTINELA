from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentAcceptedResponse(BaseModel):
    """Respuesta 202 Accepted para POST /documents."""

    model_config = ConfigDict(populate_by_name=True)

    document_id: UUID = Field(alias="documentId", serialization_alias="documentId")
    blob_name: str = Field(alias="blobName", serialization_alias="blobName")
    status: str = "accepted"
