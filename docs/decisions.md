# Decisiones de diseño (ADR) — CENTINELA

Registro de decisiones arquitectónicas relevantes.

---

## ADR-001: Clean Architecture

- **Estado:** Aceptada
- **Contexto:** Se necesita un backend mantenible, testeable y desacoplado de proveedores cloud.
- **Decisión:** Organizar el código en capas `domain`, `application`, `infrastructure` y `presentation`.
- **Consecuencias:** Mayor estructura inicial; menor acoplamiento a Azure/frameworks.

---

## ADR-002: FastAPI como framework de presentación

- **Estado:** Aceptada
- **Contexto:** Se requiere una API REST tipada y con documentación OpenAPI.
- **Decisión:** Usar FastAPI en `presentation`.
- **Consecuencias:** Dependencia del ecosistema ASGI; buena DX y tipado con Pydantic.

---

## ADR-003: Clave de partición `/accountId` en el almacén NoSQL

- **Estado:** Aceptada
- **Contexto:** Las transacciones y sus scores se guardan en Azure Cosmos DB for NoSQL (free tier). La consulta primaria (req. 2.1) es el historial por cuenta; la clave de partición no se puede cambiar tras la primera escritura.
- **Decisión:** Particionar por `/accountId`.
- **Consecuencias:** El historial por cuenta toca una sola partición (bajo costo en RU); las consultas entre cuentas hacen fan-out. Alternativas descartadas: `/id` (rompe la consulta primaria), `/date` (partición caliente en escritura), `/accountId_yyyymm` (reservada como migración si una cuenta supera 20 GB). Detalle en [`nosql.md`](./nosql.md).

---

## ADR-004: Consistencia `Session` en Cosmos DB

- **Estado:** Aceptada
- **Contexto:** El motor de scoring lee por cuenta el historial que él mismo escribe; se busca baja latencia y bajo costo en RU sin leer scores desactualizados.
- **Decisión:** Usar nivel de consistencia `Session` (read-your-writes por sesión).
- **Consecuencias:** Menor latencia/costo que `Strong`/`Bounded Staleness`; se evita el riesgo de `Eventual`.

---

## ADR-005: Expiración por TTL alineada a las ventanas de las reglas

- **Estado:** Aceptada
- **Contexto:** Las reglas de fraude evalúan ventanas temporales móviles; los datos deben sobrevivir a la ventana más amplia, y el free tier premia liberar almacenamiento.
- **Decisión:** TTL por defecto del contenedor de ~90 días (`COSMOS_TTL_SECONDS`), sobreescribible por item.
- **Consecuencias:** Cosmos elimina transacciones vencidas automáticamente; el TTL se ajusta si cambia la ventana máxima de las reglas. Detalle en [`nosql.md`](./nosql.md).
