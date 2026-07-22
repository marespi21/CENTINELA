from __future__ import annotations

from app.domain.repositories.secret_provider import SecretProvider


class AzureKeyVaultSecretProvider(SecretProvider):
    """Adaptador de Azure Key Vault (módulo seguridad).

    Autenticación por Managed Identity (DefaultAzureCredential), sin
    credenciales en código. Requiere que la identidad tenga el rol
    'Key Vault Secrets User' (ver infra/security.sh).

    El SDK se importa de forma perezosa.
    """

    def __init__(self, vault_url: str) -> None:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        self._client = SecretClient(
            vault_url=vault_url,
            credential=DefaultAzureCredential(),
        )

    def get_secret(self, name: str) -> str | None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return self._client.get_secret(name).value
        except ResourceNotFoundError:
            return None
