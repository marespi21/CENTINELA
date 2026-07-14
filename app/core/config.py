"""Application configuration.

Settings are loaded from environment variables (optionally from a local
``.env`` file via python-dotenv) and exposed as a typed, immutable object.
``pydantic-settings`` is intentionally NOT used because it is not part of
``requirements.txt``; a plain pydantic ``BaseModel`` fed from ``os.environ``
provides the same strong typing without a new dependency.

Two run modes are selected through the ``APP_ENV`` variable:

* ``local`` (default): talks to the Azurite emulator using an explicit Azure
  Storage connection string read from the environment.
* ``azure``: authenticates with :class:`DefaultAzureCredential` and reads the
  storage connection string as a secret from Azure Key Vault. The Azure
  resources do not exist yet, so this path is implemented but never the
  default in Week 1.

No real secrets live in this file. The only connection string shipped in
``.env.example`` is the well-known, public Azurite development key.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel

from app.infrastructure.azure.keyvault import KeyVaultClient

AppEnv = Literal["local", "azure"]
LogFormat = Literal["json", "console"]


class Settings(BaseModel):
    """Typed, read-only application settings."""

    model_config = {"frozen": True}

    # --- General ---------------------------------------------------------
    app_env: AppEnv = "local"
    app_name: str = "Centinela API"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    log_format: LogFormat = "json"

    # --- Azure Storage ---------------------------------------------------
    storage_connection_string: str
    transactions_container: str = "transactions"
    uploads_container: str = "uploads"
    transactions_queue: str = "transactions"

    # --- Azure Key Vault (azure mode only) -------------------------------
    key_vault_name: str | None = None


def _resolve_storage_connection_string(app_env: str) -> str:
    """Obtain the storage connection string for the active run mode."""
    if app_env == "azure":
        vault_name = os.environ.get("KEY_VAULT_NAME", "")
        secret_name = os.environ.get(
            "KEY_VAULT_STORAGE_SECRET", "storage-connection-string"
        )
        return KeyVaultClient(vault_name).get_secret(secret_name)

    # Local mode: read the explicit Azurite connection string.
    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise RuntimeError(
            "AZURE_STORAGE_CONNECTION_STRING is required in local mode. "
            "Copy .env.example to .env before starting the app."
        )
    return connection_string


@lru_cache
def get_settings() -> Settings:
    """Build and cache the application settings from the environment."""
    load_dotenv()  # no-op inside the container (env comes from env_file)
    app_env = os.environ.get("APP_ENV", "local")
    # Default to human-readable "console" logs in local mode and structured
    # "json" logs in azure mode (for Azure log ingestion); LOG_FORMAT overrides.
    log_format = os.environ.get("LOG_FORMAT") or (
        "console" if app_env == "local" else "json"
    )
    return Settings(
        app_env=app_env,  # validated against AppEnv by pydantic
        app_name=os.environ.get("APP_NAME", "Centinela API"),
        app_version=os.environ.get("APP_VERSION", "0.1.0"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        log_format=log_format,  # validated against LogFormat by pydantic
        storage_connection_string=_resolve_storage_connection_string(app_env),
        transactions_container=os.environ.get(
            "BLOB_CONTAINER_TRANSACTIONS", "transactions"
        ),
        uploads_container=os.environ.get("BLOB_CONTAINER_UPLOADS", "uploads"),
        transactions_queue=os.environ.get("QUEUE_TRANSACTIONS", "transactions"),
        key_vault_name=os.environ.get("KEY_VAULT_NAME"),
    )
