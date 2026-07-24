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

---

## ADR-009: Umbral de scoring de fraude y criterio de decisión

- **Estado:** Aceptada
- **Autor:** Andrés
- **Contexto:** El motor suma puntos de 4 reglas (velocidad 25, monto atípico 30, geo-imposible 45, comercio de riesgo 20) y abre un caso si el score supera un umbral. El umbral fija el compromiso entre **falsos positivos** (molestar a clientes legítimos) y **fraude no detectado**.
- **Decisión:** Umbral por defecto **50**, configurable por app setting `FRAUD_SCORE_THRESHOLD` (sin redeploy). Con estos pesos, **ninguna regla por sí sola abre un caso**: se exige corroboración (dos señales, o una fuerte + una débil). La geo-imposible es la de mayor peso pero sola (45) no alcanza el umbral, para no disparar casos por ruido de geolocalización (VPN, GPS impreciso).
- **Consecuencias:** Menos falsos positivos a cambio de dejar pasar transacciones con una única señal débil. El umbral se sube (más estricto, menos casos) o se baja (más sensible) sin tocar el código. Detalle y escenarios en [`fraud_scoring.md`](./fraud_scoring.md).

---

## ADR-010: Mensajería asíncrona frente a invocación directa del motor

- **Estado:** Aceptada
- **Autor:** Camila
- **Contexto:** Tras persistir una transacción, el sistema debe analizarla con el motor de scoring. Invocar el motor desde la API acoplaría latencia, fallos y escalado del scoring a la ruta crítica de ingesta, y violaría la restricción de la semana 2 (la API debe responder antes de que termine el scoring).
- **Decisión:** La API publica un evento en Azure Queue Storage (`transactions`) y responde `202 Accepted`. El motor (Azure Function) se activa solo por ese mensaje. Queda **prohibido** llamar al scoring desde el endpoint.
- **Consecuencias:** Latencia de respuesta independiente del análisis; el scoring puede reiniciarse o escalar sin tumbar la API; se habilita la Semana 3 (explicador) sobre el mismo flujo de eventos. Detalle en [`messaging.md`](./messaging.md).

---

## ADR-011: Evento de notificación vs cola con garantía de entrega

- **Estado:** Aceptada
- **Autor:** Camila
- **Contexto:** Hay dos propósitos distintos: (1) avisar de que llegó una transacción para analizarla; (2) asegurar que un caso de fraude abierto llegue a la gestión de casos aunque el consumidor esté caído.
- **Decisión:**
  - **Cola `transactions`:** distribución del evento de transacción recibida (API → scoring). Es el disparador del motor.
  - **Cola `cases`:** cola durable scoring → gestión de casos. Azure Queue retiene mensajes hasta que el consumidor los procesa y elimina; si el consumidor está detenido, **cero pérdida**.
- **Consecuencias:** Separar ambos mecanismos evita confundir “notificar trabajo” con “garantizar procesamiento de un caso”. La prueba de desacoplamiento (`test_messaging_decoupling.py`) verifica el comportamiento con consumidor detenido/reactivado. Detalle en [`messaging.md`](./messaging.md).
