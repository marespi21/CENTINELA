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

## ADR-003: Modelo Relacional y Auditoría Inmutable para Gestión de Casos

- **Estado:** Aceptada
- **Autor:** Juan José Guarín
- **Contexto:** La gestión de casos de fraude requiere integridad transaccional ACID, relaciones estructuradas entre entidades (Casos, Estados, Asignaciones, Resoluciones) y una trazabilidad inmutable sin posibilidad de alteración histórica.
- **Decisión:** Implementar un motor de base de datos relacional (PostgreSQL en Azure Flexible Server / Azure SQL) estructurado en modelo entidad-relación con FKs estrictas y una tabla `auditoria_casos` append-only resguardada por triggers plpgsql que bloquean `UPDATE` y `DELETE`.
- **Consecuencias:** Cumplimiento normativo y de auditoría estricto; prevención total de manipulación de historial de investigación de casos.

---

## ADR-004: Aislamiento Completo de Red para el Almacén de Casos

- **Estado:** Aceptada
- **Autor:** Juan José Guarín
- **Contexto:** Los almacenes de datos sensibles no deben ser accesibles directamente desde Internet para minimizar la superficie de ataque.
- **Decisión:** Desplegar la base de datos dentro de una subred dedicada (`subnet-data` - 10.0.2.0/24) con `Public Network Access = Disabled`. Integrar la comunicación exclusivamente desde la subred de aplicación (`subnet-app` - 10.0.1.0/24) mediante reglas de Network Security Group (NSG).
- **Consecuencias:** Cero acceso directo desde IP públicas; cualquier intento de conexión desde Internet resulta en rechazo o timeout.

---

## ADR-005: Estrategia de Respaldos Automáticos y Continuidad en Azure Free Tier

- **Estado:** Aceptada
- **Autor:** Juan José Guarín
- **Contexto:** Garantizar la continuidad del negocio y recuperación ante fallos dentro de las restricciones de cuota y costos del nivel gratuito (Free Tier).
- **Decisión:** Configurar **Automated Daily Backups** nativos de Azure con una retención de 7 días, habilitando **Point-In-Time Restore (PITR)** vía registros WAL (Write-Ahead Logging).
- **Consecuencias:** Objetivo de Punto de Recuperación (RPO) < 5 minutos y Objetivo de Tiempo de Recuperación (RTO) < 30 minutos sin incurrir en costos adicionales.

---

## ADR-006: Clave de partición `/accountId` en el almacén NoSQL

- **Estado:** Aceptada
- **Autor:** Chanti / Jorge
- **Contexto:** Las transacciones y sus scores se guardan en Azure Cosmos DB for NoSQL (free tier). La consulta primaria (req. 2.1) es el historial por cuenta; la clave de partición no se puede cambiar tras la primera escritura.
- **Decisión:** Particionar por `/accountId`.
- **Consecuencias:** El historial por cuenta toca una sola partición (bajo costo en RU); las consultas entre cuentas hacen fan-out. Alternativas descartadas: `/id` (rompe la consulta primaria), `/date` (partición caliente en escritura), `/accountId_yyyymm` (reservada como migración si una cuenta supera 20 GB). Detalle en [`nosql.md`](./nosql.md).

---

## ADR-007: Consistencia `Session` en Cosmos DB

- **Estado:** Aceptada
- **Autor:** Chanti / Jorge
- **Contexto:** El motor de scoring lee por cuenta el historial que él mismo escribe; se busca baja latencia y bajo costo en RU sin leer scores desactualizados.
- **Decisión:** Usar nivel de consistencia `Session` (read-your-writes por sesión).
- **Consecuencias:** Menor latencia/costo que `Strong`/`Bounded Staleness`; se evita el riesgo de `Eventual`.

---

## ADR-008: Expiración por TTL alineada a las ventanas de las reglas

- **Estado:** Aceptada
- **Autor:** Chanti / Jorge
- **Contexto:** Las reglas de fraude evalúan ventanas temporales móviles; los datos deben sobrevivir a la ventana más amplia, y el free tier premia liberar almacenamiento.
- **Decisión:** TTL por defecto del contenedor de ~90 días (`COSMOS_TTL_SECONDS`), sobreescribible por item.
- **Consecuencias:** Cosmos elimina transacciones vencidas automáticamente; el TTL se ajusta si cambia la ventana máxima de las reglas. Detalle en [`nosql.md`](./nosql.md).
