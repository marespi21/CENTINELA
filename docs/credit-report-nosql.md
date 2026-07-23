# Reporte de crédito consumido — Almacén NoSQL (entregable 13)

Módulo Chanti · Azure Cosmos DB for NoSQL · Requerimiento 2.1 (semana 2).

Este reporte documenta el crédito consumido por el almacén de transacciones y
demuestra que opera **dentro del nivel gratuito**. Los valores marcados como
_(llenar)_ se completan tras ejecutar el despliegue y la verificación en Azure.

## 1. Configuración desplegada

| Parámetro | Valor |
|-----------|-------|
| Cuenta | `cosmos-centinela-dev` |
| API | NoSQL (SQL API), `GlobalDocumentDB` |
| Nivel gratuito | **Habilitado** (`--enable-free-tier true`) |
| Throughput | `400 RU/s` provisionado (manual) |
| Consistencia | `Session` |
| Clave de partición | `/accountId` |
| TTL por defecto | `7776000 s` (~90 días) |
| Región | `eastus` |

## 2. Límites del free tier vs. consumo

El nivel gratuito de Cosmos DB descuenta de forma permanente, por cuenta:

| Recurso | Free tier (gratis) | Aprovisionado | Margen |
|---------|--------------------|---------------|--------|
| Throughput | **1000 RU/s** | 400 RU/s | 600 RU/s sin usar |
| Almacenamiento | **25 GB** | _(llenar: `az cosmosdb sql container show` → tamaño)_ | — |

Mientras se respeten `≤ 1000 RU/s` y `≤ 25 GB`, el costo del servicio es
**0 USD** y **no consume crédito de la suscripción**. Con 400 RU/s el contenedor
está por debajo del tope y deja margen para picos de escritura.

> Nota (independencia crédito/cuota, req. 2.1): el free tier de Cosmos DB no
> depende del saldo de crédito; es un descuento permanente sobre la cuenta. El
> límite de gasto de la suscripción sigue aplicando al resto de recursos.

## 3. Crédito consumido observado

Ejecutar y registrar aquí lo que reporta el portal / CLI de costos:

| Concepto | Valor |
|----------|-------|
| Costo Cosmos DB (mes en curso) | _(llenar: `az consumption usage list` filtrado por el recurso)_ |
| RU/s facturadas por encima del free tier | _(llenar; esperado: 0)_ |
| Almacenamiento facturado sobre 25 GB | _(llenar; esperado: 0)_ |
| **Crédito consumido por el almacén NoSQL** | **_(llenar; esperado: 0 USD)_** |

Relación con el budget (`infra/budget.sh`, 50 USD/mes): el almacén NoSQL no
debería mover la aguja del presupuesto mientras se mantenga en el free tier.

## 4. Evidencia de partición única (criterio de aceptación)

Salida de `python scripts/cosmos_partition_demo.py` (pegar la corrida real):

```
Historial de la cuenta 'acc-001':
  CON clave de partición (1 partición) : <n> items · <RU> RU
  SIN clave de partición (fan-out)     : <n> items · <RU> RU
```

- **RU de la consulta dirigida (una partición):** _(llenar)_
- **RU del fan-out (misma consulta sin pk):** _(llenar)_

La consulta de historial con `partition_key` se enruta a una sola partición
física: su costo en RU es proporcional al resultado y no al total de datos, lo
que confirma el criterio de aceptación.

## 5. Cómo reproducir

```bash
# Costo del recurso en el mes
az consumption usage list --query \
  "[?contains(instanceName, 'cosmos-centinela-dev')].{fecha:usageStart, costo:pretaxCost, moneda:currency}" \
  -o table

# Tamaño / throughput actuales
az cosmosdb sql container throughput show \
  -a cosmos-centinela-dev -g rg-centinela-dev -d centinela -n transactions -o table

# Evidencia de partición única
python scripts/cosmos_partition_demo.py
```

---

_Última actualización: pendiente de la primera corrida en Azure._
