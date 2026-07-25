# Arquitectura — CENTINELA

## Visión general

CENTINELA sigue **Clean Architecture** / **Arquitectura Hexagonal**, con dependencias que apuntan hacia el dominio.

## Capas

| Capa | Responsabilidad |
|------|-----------------|
| **domain** | Entidades, value objects, puertos de repositorio y excepciones de negocio |
| **application** | Casos de uso, DTOs e interfaces de aplicación |
| **infrastructure** | Implementaciones (Azure, persistencia, config, logging) |
| **presentation** | API HTTP (FastAPI), schemas, middlewares y manejo de errores |

## Flujo de dependencias

```
presentation → application → domain
       ↓            ↓
infrastructure ─────┘
```

La capa de dominio no depende de frameworks ni de infraestructura.

## Backend

Punto de entrada: `backend/app/main.py`.

---

## Almacén Relacional de Casos y Auditoría Inmutable (Juan José Guarín)

### 1. Componente y Motor de Persistencia
- **Motor:** Azure Database for PostgreSQL Flexible Server (`Standard_B1ms` - Free Tier).
- **Esquema Relacional (ACID):** Entidades `casos`, `estados`, `asignaciones`, `resoluciones` y `auditoria_casos`.

### 2. Aislamiento de Red y Seguridad
- **Subred Delegada:** Desplegado en `subnet-db` (`10.0.3.0/24`) con delegación `Microsoft.DBforPostgreSQL/flexibleServers`.
- **Visibilidad:** `Public Network Access = Disabled`. Totalmente inalcanzable desde Internet.
- **Acceso:** Permitido únicamente desde la subred de aplicación (`subnet-app` - `10.0.1.0/24`) vía reglas de NSG (`Allow-App-Subnet-To-PostgreSQL`).

### 3. Integridad y Auditoría Inmutable (Append-Only)
- **Trazabilidad:** Captura automática de cambios en `casos`, `asignaciones` y `resoluciones`.
- **Usuario de Aplicación:** Función `get_app_user()` que extrae la variable de sesión `app.current_user` para registrar el usuario real de aplicación en lugar del login genérico de BD.
- **Regla de Inmutabilidad:** Trigger `trg_prevent_audit_tampering` en PL/pgSQL que rechaza con excepción explícita cualquier intento de `UPDATE` o `DELETE` sobre `auditoria_casos`.

### 4. Decisiones de Arquitectura Asociadas (ADRs)
- **[ADR-003](decisions.md#adr-003-modelo-relacional-y-auditoria-inmutable-para-gestion-de-casos):** Modelo Relacional y Auditoría Inmutable para Gestión de Casos.
- **[ADR-004](decisions.md#adr-004-aislamiento-completo-de-red-para-el-almacen-de-casos):** Aislamiento Completo de Red para el Almacén de Casos.
- **[ADR-005](decisions.md#adr-005-estrategia-de-respaldos-automaticos-y-continuidad-en-azure-free-tier):** Estrategia de Respaldos Automáticos y Continuidad en Azure Free Tier.
- **Especificación Técnica Completa:** [`docs/cases_store_spec.md`](cases_store_spec.md).

---

## Persistencia de transacciones (NoSQL)

Las transacciones y sus scores se almacenan en **Azure Cosmos DB for NoSQL**
(free tier). Es un almacén distinto y complementario al relacional de casos:
NoSQL para el flujo transaccional de alto volumen, relacional para la gestión de
casos con integridad ACID. Las decisiones de clave de partición, consistencia y
TTL están en [`decisions.md`](./decisions.md) (ADR-006…008) y detalladas en
[`nosql.md`](./nosql.md).

---

## Motor de scoring de fraude (serverless, Andrés)

Función **serverless** disparada por el **evento de transacción** (cola
`transactions`), nunca por la API. Consulta el historial de la cuenta, evalúa 4
reglas (velocidad, monto atípico, geo-imposible, comercio de riesgo), suma
puntos, persiste el score + detalle y publica un caso si supera el umbral. El
umbral es configurable sin redeploy. Decisión del umbral en
[`decisions.md`](./decisions.md) (ADR-009); detalle en
[`fraud_scoring.md`](./fraud_scoring.md).

---

## Mensajería y desacoplamiento (Camila)

La API **no** invoca el motor: tras persistir publica en la cola
`transactions` y responde `202`. Los casos que superan el umbral van a la cola
durable `cases`. Decisiones en [`decisions.md`](./decisions.md) (ADR-010,
ADR-011); detalle en [`messaging.md`](./messaging.md).

---

## Seguridad: secretos, identidad y rate limiting (Lucas)

Dos protecciones transversales sobre la API:

- **Secretos en Key Vault + Managed Identity.** Ninguna credencial vive en el
  código, el repo ni el historial de git (auditado). Los componentes se
  autentican con Managed Identity (`DefaultAzureCredential`) y leen los secretos
  de Azure Key Vault con RBAC de menor privilegio. El proveedor de secretos se
  elige en el composition root según `KEY_VAULT_URL`.
- **Rate limiting por origen.** Un middleware limita las peticiones por IP en una
  ventana deslizante y responde **429** al exceder, para proteger la
  disponibilidad del servicio de crédito ante saturación.

Decisiones en [`decisions.md`](./decisions.md) (ADR-012, ADR-013); detalle en
[`security.md`](./security.md).

---

## Explicador de casos (Semana 3)

Cuando el motor abre un caso, un **explicador** transforma el `ScoringResult` y
su evidencia en una **explicación legible** para el analista (resumen + razones
por regla con su detalle). Es un contrato compartido: la mensajería lo publica
en la cola de casos, gestión de casos lo persiste y expone vía
`GET /cases/{caseId}`, y seguridad protege ese endpoint. Decisión en
[`decisions.md`](./decisions.md) (ADR-014); detalle y contrato JSON en
[`explainability.md`](./explainability.md).
