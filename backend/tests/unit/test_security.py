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
