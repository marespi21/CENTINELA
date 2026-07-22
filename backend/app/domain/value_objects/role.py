from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """Roles de acceso del sistema (módulo seguridad).

    - ADMINISTRADOR: control total.
    - ANALISTA: opera sobre casos/transacciones.
    - AUDITOR: solo lectura/consulta.
    - SERVICIO: identidad de servicio (App Service / Managed Identity).
    """

    ADMINISTRADOR = "administrador"
    ANALISTA = "analista"
    AUDITOR = "auditor"
    SERVICIO = "servicio"
