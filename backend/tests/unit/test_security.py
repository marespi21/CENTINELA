from __future__ import annotations

from app.domain.value_objects.role import Role
from app.infrastructure.repositories.in_memory_secret_provider import (
    InMemorySecretProvider,
)
from app.presentation.api.dependencies.security import AuthPolicy


def test_secret_provider_returns_stored_secret() -> None:
    provider = InMemorySecretProvider({"storage-conn": "secret-value"})
    assert provider.get_secret("storage-conn") == "secret-value"


def test_secret_provider_returns_none_for_unknown() -> None:
    provider = InMemorySecretProvider()
    assert provider.get_secret("missing") is None


def test_auth_policy_resolves_key_to_role() -> None:
    policy = AuthPolicy(enabled=True, keys={"k": Role.ANALISTA})
    assert policy.resolve("k") is Role.ANALISTA
    assert policy.resolve("unknown") is None


def test_auth_policy_from_settings_without_secret_provider() -> None:
    """Sin SecretProvider, lee desde env (vacío por defecto en tests)."""
    policy = AuthPolicy.from_settings(secret_provider=None)
    assert not policy.keys  # API_KEYS no está definida en test env


def test_auth_policy_from_settings_falls_back_to_env_when_vault_empty() -> None:
    """SecretProvider devuelve None → fallback a variable de entorno."""
    provider = InMemorySecretProvider({"some-secret": "value"})
    policy = AuthPolicy.from_settings(secret_provider=provider)
    # No hay "api-keys" en el provider, y API_KEYS no está en test env
    assert not policy.keys


def test_auth_policy_from_settings_with_secret_provider() -> None:
    """SecretProvider con 'api-keys' sobreescribe variable de entorno."""
    provider = InMemorySecretProvider({"api-keys": "vault-key:analista"})
    policy = AuthPolicy.from_settings(secret_provider=provider)
    assert policy.resolve("vault-key") is Role.ANALISTA
    assert len(policy.keys) == 1


def test_auth_policy_from_settings_respects_auth_enabled_from_env() -> None:
    """El flag auth_enabled se toma de settings, no del SecretProvider."""
    provider = InMemorySecretProvider({"api-keys": "k:administrador"})
    policy = AuthPolicy.from_settings(secret_provider=provider)
    # auth_enabled por defecto es False en tests (sin env var)
    assert policy.enabled is False
