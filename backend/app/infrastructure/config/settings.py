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

    # Documentos / Storage / Queue (módulos Jorge + Samuel)
    # STORAGE_ACCOUNT es el nombre de la cuenta; de él se derivan los
    # endpoints de blob y queue (que son distintos entre sí).
    storage_account: str = os.getenv("STORAGE_ACCOUNT", "")
    storage_connection_string: str = os.getenv("STORAGE_CONNECTION_STRING", "")
    blob_container: str = os.getenv("BLOB_CONTAINER", "documents")
    documents_queue: str = os.getenv("DOCUMENTS_QUEUE", "documents")
    max_document_mb: int = int(os.getenv("MAX_DOCUMENT_MB", "5"))
    allowed_document_types: str = os.getenv(
        "ALLOWED_DOCUMENT_TYPES",
        "application/pdf,image/png,image/jpeg",
    )

    # Seguridad (módulo Lukas)
    auth_enabled: bool = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    # Mapa "clave:rol" separado por comas, p.ej. "svc-key:servicio,adm-key:administrador".
    # En producción estas claves viven en Key Vault, no en el repo.
    api_keys: str = os.getenv("API_KEYS", "")
    key_vault_url: str = os.getenv("KEY_VAULT_URL", "")

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

    @property
    def blob_endpoint(self) -> str:
        if self.storage_account:
            return f"https://{self.storage_account}.blob.core.windows.net"
        return ""

    @property
    def queue_endpoint(self) -> str:
        if self.storage_account:
            return f"https://{self.storage_account}.queue.core.windows.net"
        return ""


settings = Settings()
