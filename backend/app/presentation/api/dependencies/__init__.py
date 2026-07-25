from __future__ import annotations

from functools import lru_cache

from app.domain.repositories.secret_provider import SecretProvider
from app.infrastructure.config.settings import settings
from app.infrastructure.repositories.in_memory_secret_provider import (
    InMemorySecretProvider,
)


@lru_cache(maxsize=1)
def get_secret_provider() -> SecretProvider:
    """Punto de composición del proveedor de secretos.

    - Con KEY_VAULT_URL configurado → Azure Key Vault (Managed Identity).
    - Sin configuración → memoria / variables de entorno (dev/test).
    """
    if settings.key_vault_url:
        from app.infrastructure.azure.key_vault import (
            AzureKeyVaultSecretProvider,  # lazy import
        )

        return AzureKeyVaultSecretProvider(vault_url=settings.key_vault_url)
    return InMemorySecretProvider()

