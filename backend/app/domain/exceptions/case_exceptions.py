from __future__ import annotations


class CaseNotFoundError(Exception):
    """No existe un caso con el identificador dado."""

    def __init__(self, case_id: str) -> None:
        self.case_id = case_id
        super().__init__(f"Case '{case_id}' not found")
