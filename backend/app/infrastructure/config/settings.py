"""Configuración de la aplicación desde variables de entorno."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Ajustes base de Centinela (Día 1)."""

    app_name: str = os.getenv("APP_NAME", "Centinela")
    api_version: str = os.getenv("API_VERSION", "1.0")
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Documentos / Storage / Queue (módulo Jorge)
    storage_connection_string: str = os.getenv("STORAGE_CONNECTION_STRING", "")
    storage_account_url: str = os.getenv("STORAGE_ACCOUNT_URL", "")
    blob_container: str = os.getenv("BLOB_CONTAINER", "documents")
    documents_queue: str = os.getenv("DOCUMENTS_QUEUE", "documents")
    max_document_mb: int = int(os.getenv("MAX_DOCUMENT_MB", "5"))
    allowed_document_types: str = os.getenv(
        "ALLOWED_DOCUMENT_TYPES",
        "application/pdf,image/png,image/jpeg",
    )

    @property
    def max_document_bytes(self) -> int:
        return self.max_document_mb * 1024 * 1024

    @property
    def allowed_document_types_set(self) -> frozenset[str]:
        return frozenset(
            item.strip()
            for item in self.allowed_document_types.split(",")
            if item.strip()
        )


settings = Settings()
