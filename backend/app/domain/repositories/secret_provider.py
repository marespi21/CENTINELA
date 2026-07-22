from __future__ import annotations

from abc import ABC, abstractmethod


class SecretProvider(ABC):
    """Puerto para obtener secretos (módulo seguridad).

    Implementaciones: memoria/entorno (dev) o Azure Key Vault (prod),
    sin credenciales en código.
    """

    @abstractmethod
    def get_secret(self, name: str) -> str | None:
        """Devuelve el valor del secreto o None si no existe."""
        raise NotImplementedError
