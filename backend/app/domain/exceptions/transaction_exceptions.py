"""Excepciones de dominio para Centinela."""


class DomainError(Exception):
    """Error base del dominio."""


class DuplicateTransactionError(DomainError):
    """La transacción ya fue recibida anteriormente."""

    def __init__(self, transaction_id: str) -> None:
        self.transaction_id = transaction_id
        super().__init__(f"Transaction already exists: {transaction_id}")


class InvalidTransactionError(DomainError):
    """La transacción no cumple reglas mínimas de negocio."""
