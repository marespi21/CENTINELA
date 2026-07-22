"""Excepciones de dominio para autenticación y autorización."""

from app.domain.exceptions.transaction_exceptions import DomainError


class UnauthorizedError(DomainError):
    """Falta credencial o es inválida (HTTP 401)."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message)


class ForbiddenError(DomainError):
    """Autenticado pero sin permiso para la operación (HTTP 403)."""

    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message)
