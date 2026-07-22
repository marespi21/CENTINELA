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


settings = Settings()
