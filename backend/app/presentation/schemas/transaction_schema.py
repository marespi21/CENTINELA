"""Contrato HTTP de una transacción (Día 1 — solo diseño).

Campos del contrato POST /transactions (Semana 1):

Campo              | Tipo           | Obligatorio | Descripción
-------------------|----------------|-------------|------------------------------------------
transactionId      | UUID           | Sí          | Identificador único de la transacción
accountId          | String         | Sí          | Cuenta que origina la transacción
amount             | Decimal        | Sí          | Valor monetario
currency           | String         | Sí          | COP, USD...
merchantId         | String         | Sí          | Comercio destino
merchantCategory   | String         | Sí          | Categoría del comercio
timestamp          | DateTime UTC   | Sí          | Fecha generada por el servidor
latitude           | Decimal        | Sí          | Latitud
longitude          | Decimal        | Sí          | Longitud

Notas:
- Semana 1: solo validar, guardar y responder 202 Accepted.
- No se calcula score, no se consulta historial, no se abren casos, no se detecta fraude.
- Los schemas Pydantic se implementarán en un día posterior.
"""
