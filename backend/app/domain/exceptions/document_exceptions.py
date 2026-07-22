"""Excepciones de dominio para documentos."""

from app.domain.exceptions.transaction_exceptions import DomainError


class InvalidDocumentError(DomainError):
    """Base para documentos que no cumplen reglas de negocio."""


class EmptyDocumentError(InvalidDocumentError):
    """El documento no tiene contenido."""

    def __init__(self) -> None:
        super().__init__("Document is empty")


class InvalidDocumentTypeError(InvalidDocumentError):
    """El tipo de archivo no está permitido."""

    def __init__(self, content_type: str) -> None:
        self.content_type = content_type
        super().__init__(f"Unsupported document type: {content_type}")


class DocumentTooLargeError(InvalidDocumentError):
    """El documento excede el tamaño máximo permitido."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(f"Document too large: {size_bytes} bytes (max {max_bytes})")
