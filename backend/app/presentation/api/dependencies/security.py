from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Header

from app.domain.exceptions.auth_exceptions import ForbiddenError, UnauthorizedError
from app.domain.repositories.secret_provider import SecretProvider
from app.domain.value_objects.role import Role
from app.infrastructure.config.settings import settings
from app.presentation.api.dependencies import get_secret_provider


@dataclass(frozen=True)
class Principal:
    """Identidad autenticada de quien hace la petición."""

    role: Role
    api_key: str | None = None


@dataclass(frozen=True)
class AuthPolicy:
    """Política de autorización: si está activa y el mapa clave->rol."""

    enabled: bool
    keys: dict[str, Role] = field(default_factory=dict)

    def resolve(self, api_key: str) -> Role | None:
        return self.keys.get(api_key)

    @classmethod
    def from_settings(cls, secret_provider: SecretProvider | None = None) -> AuthPolicy:
        """Construye la política desde las fuentes de configuración.

        Prioridad para las API keys:
        1. Key Vault (secreto 'api-keys').
        2. Variable de entorno API_KEYS.
        """
        raw_keys: str = ""

        # Intentar desde Key Vault primero
        if secret_provider:
            vault_value = secret_provider.get_secret("api-keys")
            if vault_value:
                raw_keys = vault_value

        # Fallback a variable de entorno
        if not raw_keys:
            raw_keys = settings.api_keys

        keys: dict[str, Role] = {}
        for pair in raw_keys.split(","):
            pair = pair.strip()
            if not pair or ":" not in pair:
                continue
            api_key, _, role_name = pair.partition(":")
            try:
                keys[api_key.strip()] = Role(role_name.strip().lower())
            except ValueError:
                # Rol desconocido: se ignora la entrada.
                continue
        return cls(enabled=settings.auth_enabled, keys=keys)


def get_auth_policy() -> AuthPolicy:
    """Composition root de autorización (override en tests)."""
    return AuthPolicy.from_settings(secret_provider=get_secret_provider())


def require_roles(*allowed_roles: Role):
    """Dependency de FastAPI que exige uno de los roles dados.

    Si AUTH_ENABLED es falso (dev/local), no bloquea y asume rol SERVICIO.
    Con auth activa: 401 si falta/invalida la clave, 403 si el rol no aplica.
    """

    async def dependency(
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        policy: AuthPolicy = Depends(get_auth_policy),
    ) -> Principal:
        if not policy.enabled:
            return Principal(role=Role.SERVICIO)

        if not x_api_key:
            raise UnauthorizedError("Missing API key")

        role = policy.resolve(x_api_key)
        if role is None:
            raise UnauthorizedError("Invalid API key")

        if allowed_roles and role not in allowed_roles:
            raise ForbiddenError(
                f"Role '{role.value}' not allowed for this operation"
            )

        return Principal(role=role, api_key=x_api_key)

    return dependency
