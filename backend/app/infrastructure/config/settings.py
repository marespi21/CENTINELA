"""Configuración de la aplicación desde variables de entorno."""

import os
from dataclasses import dataclass
from decimal import Decimal

from dotenv import load_dotenv

from app.domain.value_objects.scoring_config import ScoringConfig

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Ajustes base de Centinela (Día 1)."""

    app_name: str = os.getenv("APP_NAME", "Centinela")
    api_version: str = os.getenv("API_VERSION", "1.0")
    environment: str = os.getenv("ENVIRONMENT", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

    # Documentos / Storage / Queue (módulos Jorge + Samuel + Camila)
    # STORAGE_ACCOUNT es el nombre de la cuenta; de él se derivan los
    # endpoints de blob y queue (que son distintos entre sí).
    storage_account: str = os.getenv("STORAGE_ACCOUNT", "")
    storage_connection_string: str = os.getenv("STORAGE_CONNECTION_STRING", "")
    blob_container: str = os.getenv("BLOB_CONTAINER", "documents")
    documents_queue: str = os.getenv("DOCUMENTS_QUEUE", "documents")
    # Cola de eventos de transacción (API → motor de scoring). Alias QUEUE_NAME
    # por compatibilidad con infra/deploy.sh y Azure Functions.
    transactions_queue: str = os.getenv(
        "TRANSACTIONS_QUEUE",
        os.getenv("QUEUE_NAME", "transactions"),
    )
    # Cola durable de casos (scoring → gestión de casos).
    cases_queue: str = os.getenv("CASES_QUEUE", "cases")
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

    # Rate limiting por IP (en memoria, sin Redis)
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    rate_limit_max_requests: int = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "10"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # Motor de scoring de fraude (módulo Andrés, semana 2).
    # El UMBRAL es un app setting: cambiarlo NO requiere redesplegar el código.
    fraud_score_threshold: int = int(os.getenv("FRAUD_SCORE_THRESHOLD", "50"))
    fraud_weight_velocity: int = int(os.getenv("FRAUD_WEIGHT_VELOCITY", "25"))
    fraud_weight_atypical_amount: int = int(os.getenv("FRAUD_WEIGHT_ATYPICAL_AMOUNT", "30"))
    fraud_weight_geo_impossible: int = int(os.getenv("FRAUD_WEIGHT_GEO_IMPOSSIBLE", "45"))
    fraud_weight_risky_merchant: int = int(os.getenv("FRAUD_WEIGHT_RISKY_MERCHANT", "20"))
    fraud_velocity_max_tx: int = int(os.getenv("FRAUD_VELOCITY_MAX_TX", "5"))
    fraud_velocity_window_minutes: int = int(os.getenv("FRAUD_VELOCITY_WINDOW_MIN", "10"))
    fraud_amount_factor: str = os.getenv("FRAUD_AMOUNT_FACTOR", "3.0")
    fraud_amount_min_history: int = int(os.getenv("FRAUD_AMOUNT_MIN_HISTORY", "3"))
    fraud_amount_absolute_cap: str = os.getenv("FRAUD_AMOUNT_ABSOLUTE_CAP", "1000000")
    fraud_geo_max_speed_kmh: str = os.getenv("FRAUD_GEO_MAX_SPEED_KMH", "900")
    fraud_risky_categories: str = os.getenv(
        "FRAUD_RISKY_CATEGORIES",
        "gambling,crypto,wire_transfer,gift_cards,adult",
    )

    # Almacén NoSQL (Cosmos DB) — historial de transacciones y scores del worker.
    # Sin COSMOS_ENDPOINT se usan los adaptadores en memoria (dev/test).
    cosmos_endpoint: str = os.getenv("COSMOS_ENDPOINT", "")
    cosmos_key: str = os.getenv("COSMOS_KEY", "")  # vacío => Managed Identity
    cosmos_database: str = os.getenv("COSMOS_DATABASE", "centinela")
    cosmos_container: str = os.getenv("COSMOS_CONTAINER", "transactions")

    # Almacén relacional de casos (PostgreSQL) — API de lectura de casos.
    # Sin CASES_DB_DSN se usa el adaptador en memoria (dev/test).
    cases_db_dsn: str = os.getenv("CASES_DB_DSN", "")

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

    @property
    def cosmos_configured(self) -> bool:
        """True si el worker debe usar Cosmos (no los adaptadores en memoria)."""
        return bool(self.cosmos_endpoint)

    @property
    def cases_db_configured(self) -> bool:
        """True si la API de casos debe usar PostgreSQL (no memoria)."""
        return bool(self.cases_db_dsn)

    @property
    def scoring_config(self) -> ScoringConfig:
        """Construye la config del motor desde las variables de entorno.

        Se lee en cada arranque de la función; cambiar un app setting (p. ej.
        el umbral) reinicia la función y aplica el nuevo valor sin redeploy.
        """
        categories = frozenset(
            c.strip().lower()
            for c in self.fraud_risky_categories.split(",")
            if c.strip()
        )
        return ScoringConfig(
            threshold=self.fraud_score_threshold,
            weight_velocity=self.fraud_weight_velocity,
            weight_atypical_amount=self.fraud_weight_atypical_amount,
            weight_geo_impossible=self.fraud_weight_geo_impossible,
            weight_risky_merchant=self.fraud_weight_risky_merchant,
            velocity_max_tx=self.fraud_velocity_max_tx,
            velocity_window_minutes=self.fraud_velocity_window_minutes,
            amount_factor=Decimal(self.fraud_amount_factor),
            amount_min_history=self.fraud_amount_min_history,
            amount_absolute_cap=Decimal(self.fraud_amount_absolute_cap),
            geo_max_speed_kmh=Decimal(self.fraud_geo_max_speed_kmh),
            risky_categories=categories,
        )


settings = Settings()
