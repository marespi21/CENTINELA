from __future__ import annotations

from app.domain.repositories.secret_provider import SecretProvider


class InMemorySecretProvider(SecretProvider):
    """Proveedor de secretos en memoria/entorno para desarrollo y pruebas.

    Se reemplaza por AzureKeyVaultSecretProvider en el composition root.
    """

    def __init__(self, secrets: dict[str, str] | None = None) -> None:
        self._secrets: dict[str, str] = dict(secrets or {})

    def get_secret(self, name: str) -> str | None:
        return self._secrets.get(name)
