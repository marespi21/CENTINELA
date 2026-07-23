# Almacén NoSQL de transacciones — CENTINELA (módulo Chanti)

## Objetivo

Persistir **transacciones y sus scores** en un almacén NoSQL de alto volumen de
escritura, optimizado para la **consulta de historial por cuenta**. Requerimiento
2.1 (semana 2).

## Servicio y recursos

Se usa **Azure Cosmos DB for NoSQL** (SQL API) en **nivel gratuito**.

| Recurso | Nombre (default) | Notas |
|---------|------------------|-------|
| Cuenta Cosmos DB | `cosmos-<proyecto>-<env>` (ej. `cosmos-centinela-dev`) | `GlobalDocumentDB`, free tier, único global. Una sola cuenta free-tier por suscripción. |
| Base de datos | `centinela` | — |
| Contenedor | `transactions` | pk `/accountId`, `400 RU/s`, TTL por defecto. |

Aprovisionamiento: [`infra/cosmos.sh`](../infra/cosmos.sh) (invocado por
[`infra/deploy.sh`](../infra/deploy.sh), paso 15, y ejecutable de forma
independiente). Parámetros en [`infra/variables.sh`](../infra/variables.sh)
(bloque `COSMOS_*`).

## Free tier — límites y encaje (documentado)

El nivel gratuito de Cosmos DB descuenta, por cuenta y de forma permanente:

- **1000 RU/s** de throughput provisionado.
- **25 GB** de almacenamiento.

El contenedor se aprovisiona con **400 RU/s** y una sola partición lógica por
cuenta, muy por debajo de ambos límites → **consumo de crédito esperado: 0 USD**
mientras se respeten esos topes. Detalle y evidencia en
[`credit-report-nosql.md`](./credit-report-nosql.md) (entregable 13).

## Modelo del documento

```jsonc
{
  "id": "uuid",            // id único del item dentro de la partición
  "accountId": "acc-001",  // CLAVE DE PARTICIÓN
  "amount": 1234.56,
  "score": 0.8123,         // score de fraude (lo escribe el motor de semana 2)
  "createdAt": "2026-07-23T12:00:00Z",
  "ttl": 7776000            // opcional; sobreescribe el TTL por defecto del item
}
```

---

## Decisión 1 — Clave de partición

**Seleccionada: `/accountId`.**

> La clave de partición **no se puede cambiar** tras crear el contenedor. Se fija
> en `infra/variables.sh` **antes de la primera escritura**; cambiarla exige
> recrear el contenedor y migrar los datos.

- **Qué optimiza:** la consulta primaria del sistema — *historial de una cuenta*
  (`SELECT * FROM c WHERE c.accountId = @acc`) — se enruta a **una sola
  partición**, con costo en RU proporcional al resultado y no al total de datos.
  Es también la lectura que hace el motor de scoring para evaluar reglas de
  velocidad por cuenta.
- **Distribución de escritura:** al haber muchas cuentas, las escrituras se
  reparten de forma pareja entre particiones → soporta alto volumen sin punto
  caliente, siempre que ninguna cuenta concentre un tráfico desproporcionado.
- **Qué sacrifica:** las consultas *entre cuentas* (p. ej. "todas las
  transacciones de la última hora" o "todos los scores altos globales") se
  vuelven **cross-partition (fan-out)** y cuestan más RU. Además, una cuenta muy
  activa podría acercarse al límite de **20 GB por partición lógica**.

### Alternativas descartadas

| Clave | Optimiza | Sacrifica | Por qué se descarta |
|-------|----------|-----------|---------------------|
| `/id` (o `/transactionId`) | Distribución de escritura perfecta | El historial por cuenta se vuelve fan-out | Encarece la **consulta primaria**; contradice el requerimiento 2.1. |
| `/date` (o día) | Escaneos por rango de tiempo | Punto caliente: todas las escrituras del día caen en una partición; el historial por cuenta abanica | Hot partition en escritura + historial caro. |
| `/accountId_yyyymm` (sintética compuesta) | Acota el tamaño de partición de cuentas muy activas; consultas cuenta+mes single-partition | El historial **completo** de una cuenta abanica entre meses | Se reserva como **ruta de migración** si una cuenta supera los 20 GB. |

---

## Decisión 2 — Nivel de consistencia

**Seleccionado: `Session`** (por defecto de la cuenta).

- **Impacto en latencia:** `Session` ofrece **baja latencia** de lectura y
  escritura y menor costo en RU que `Strong` / `Bounded Staleness`, garantizando
  *read-your-writes* y *monotonic reads* dentro de una misma sesión.
- **Por qué encaja:** el motor de scoring lee el historial que él mismo acaba de
  escribir por cuenta; `Session` es suficiente para esa coherencia sin pagar la
  latencia entre réplicas de `Strong`. `Eventual` se descarta porque podría leer
  scores desactualizados al evaluar reglas.

| Nivel | Latencia / costo RU | Descarte |
|-------|---------------------|----------|
| Strong | Mayor (coordina réplicas) | Innecesario para consistencia por cuenta. |
| Bounded Staleness | Media | No aporta sobre Session para este acceso. |
| **Session** | **Baja** | **Seleccionado.** |
| Consistent Prefix / Eventual | Mínima | Riesgo de leer scores viejos. |

---

## Decisión 3 — Política de expiración (TTL)

**TTL por defecto del contenedor: `7776000 s` (~90 días).** Configurado con
`--ttl` en `infra/cosmos.sh`.

- **Relación con las ventanas temporales de las reglas:** las reglas de fraude
  evalúan ventanas móviles (velocidad, acumulados) sobre el historial reciente.
  Una transacción debe **sobrevivir al menos tanto como la ventana más amplia**.
  El TTL se fija por encima de esa ventana (90 días) para no borrar datos que una
  regla aún necesita; pasado ese punto, Cosmos elimina los items automáticamente
  y libera RU/almacenamiento (relevante para el free tier).
- **Ajuste fino:** el campo `ttl` por item puede sobreescribir el default (p. ej.
  conservar más tiempo transacciones marcadas como fraude). Si la ventana más
  amplia de las reglas cambia, se actualiza `COSMOS_TTL_SECONDS` en
  `variables.sh` y se reaplica `cosmos.sh`.

---

## Despliegue y verificación

```bash
# 1) Desplegar (o como paso 15 de infra/deploy.sh)
bash infra/cosmos.sh

# 2) Verificar la partición única (criterio de aceptación)
export COSMOS_ENDPOINT="$(az cosmosdb show -n cosmos-centinela-dev -g rg-centinela-dev --query documentEndpoint -o tsv)"
export COSMOS_KEY="$(az cosmosdb keys list -n cosmos-centinela-dev -g rg-centinela-dev --query primaryMasterKey -o tsv)"
pip install -r scripts/requirements.txt
python scripts/cosmos_partition_demo.py
```

El script [`scripts/cosmos_partition_demo.py`](../scripts/cosmos_partition_demo.py)
imprime las RU (`x-ms-request-charge`) de la consulta de historial **con** y
**sin** clave de partición, evidenciando que la dirigida toca una sola partición.

## Definition of Done — mapeo de entregables

| Criterio (DoD) | Evidencia |
|----------------|-----------|
| Recurso desplegado, dentro del free tier (documentado) | `infra/cosmos.sh` + [free tier](#free-tier--límites-y-encaje-documentado) + [reporte de crédito](./credit-report-nosql.md) |
| Partition key definida **y justificada por escrito** | [Decisión 1](#decisión-1--clave-de-partición) + `COSMOS_PARTITION_KEY` |
| TTL configurado | [Decisión 3](#decisión-3--política-de-expiración-ttl) + `--ttl` en `cosmos.sh` |
| Métrica de consumo: historial de una cuenta = una partición | `scripts/cosmos_partition_demo.py` (RU) |

- **Entregable 1** — recurso NoSQL desplegado: `infra/cosmos.sh`.
- **Entregable 2** — decisiones documentadas: este documento + `docs/decisions.md`
  (ADR-003…005).
- **Entregable 13** — reporte de crédito consumido: `docs/credit-report-nosql.md`.

Revisa el PR (debe aprobar): **Juan José (Guarín)**.
