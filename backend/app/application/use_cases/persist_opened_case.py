"""Caso de uso: persistir un caso recibido de la cola `cases` (Semana 3).

Es el consumidor de mensajería (módulo Camila): parsea el mensaje y entrega el
caso a gestión de casos. La garantía de entrega la da la cola durable (Azure
Queue): si el consumidor está caído, el mensaje permanece hasta procesarse.
"""

from __future__ import annotations

from app.application.dtos.case_message_dto import opened_case_from_message
from app.domain.repositories.case_write_repository import CaseWriteRepository


class PersistOpenedCaseUseCase:
    def __init__(self, case_write_repository: CaseWriteRepository) -> None:
        self._cases = case_write_repository

    def execute(self, message: str) -> str:
        """Parsea el mensaje del caso y lo persiste; devuelve el id del caso."""
        opened_case = opened_case_from_message(message)
        return self._cases.save_opened_case(opened_case)
