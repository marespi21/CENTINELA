"""Azure Key Vault secrets client.

Reads secrets from Azure Key Vault using :class:`DefaultAzureCredential`. Used
only in the ``azure`` run mode (see :mod:`app.core.config`). The Azure
resources do not exist yet in Week 1, so this client is implemented but never
exercised by the default (local) configuration.
"""

from __future__ import annotations

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from app.core.logger import get_logger

logger = get_logger(__name__)


class KeyVaultClient:
    """Thin wrapper around ``azure-keyvault-secrets``."""

    def __init__(self, vault_name: str) -> None:
        if not vault_name:
            raise ValueError("vault_name is required to build a Key Vault client")
        self._vault_url = f"https://{vault_name}.vault.azure.net"
        self._client: SecretClient | None = None

    @property
    def client(self) -> SecretClient:
        # Lazy init: DefaultAzureCredential resolves managed identity / env /
        # Azure CLI credentials in that order, so nothing is needed locally.
        if self._client is None:
            self._client = SecretClient(
                vault_url=self._vault_url,
                credential=DefaultAzureCredential(),
            )
        return self._client

    def get_secret(self, name: str) -> str:
        """Return the value of the secret ``name`` from Key Vault."""
        logger.info("Fetching secret from Key Vault", extra={"secret": name})
        secret = self.client.get_secret(name)
        if secret.value is None:
            raise RuntimeError(f"Key Vault secret '{name}' has no value")
        return secret.value
