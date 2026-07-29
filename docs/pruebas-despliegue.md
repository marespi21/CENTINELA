# Cómo probar el despliegue

**Sprint 6 — CENTINELA sobre Azure Container Apps**

---

## Direcciones

| Qué | Dónde |
|---|---|
| **API** | `https://ca-centinela-api-dev-sp5x1.politepond-86c728aa.eastus2.azurecontainerapps.io` |
| **Consola** | `http://localhost:3001` — se arranca con `cd frontend && npm run dev` |

Clave de analista: `adm-key` (rol administrador). La consola ya la lleva
configurada en `.env.local`; el navegador nunca la ve, la usa el BFF de Next.

> **Paciencia en la primera petición.** Ambos contenedores escalan a cero: si
> llevan un rato sin uso, la primera llamada tarda unos segundos en arrancarlos.
> No es un error.

---

## Prueba 1 · La consola muestra casos reales

1. Abre `http://localhost:3001`.
2. Deberías ver la bandeja con casos de cuentas `acc-*`.
3. Entra en el detalle de uno y comprueba que aparece la explicación
   («score 50/50, 2 señales: Monto atípico, Comercio de categoría de riesgo»).

Si la bandeja sale vacía, el problema es de conexión, no de datos: comprueba que
`frontend/.env.local` apunta a la URL de arriba y no al App Service antiguo.

---

## Prueba 2 · Detectar un fraude de punta a punta

Lanza una transacción que dispare las reglas — importe alto y comercio de riesgo:

```bash
API=https://ca-centinela-api-dev-sp5x1.politepond-86c728aa.eastus2.azurecontainerapps.io

curl -s -X POST "$API/transactions" \
  -H "X-API-Key: adm-key" -H "Content-Type: application/json" \
  -d '{"transactionId":"'"$(uuidgen)"'","accountId":"acc-prueba",
       "amount":"3000000","currency":"COP","merchantId":"m1",
       "merchantCategory":"crypto","latitude":"4.7110","longitude":"-74.0721"}'
```

Responde `202 accepted` **al instante**: la API no espera al scoring.

Espera y refresca la consola. El caso aparece en **entre 20 s y 2 minutos**,
según si el worker estaba encendido o hubo que despertarlo desde cero réplicas.

Esa espera **es el comportamiento correcto**, no un fallo: es el precio del
escalado a cero, y a cambio el sistema no consume nada cuando no hay trabajo.

---

## Prueba 3 · Verificación documental (OCR)

Necesitas el `caseId` de un caso, visible en la consola o con
`curl "$API/cases?pageSize=5" -H "X-API-Key: adm-key"`.

**Comprobante que cuadra** — mismo importe que la transacción:

```bash
cat > /tmp/recibo.txt <<'EOF'
                 COMERCIO DE PRUEBA
         Fecha:  07/29/2026
         TOTAL                      3000000.00
EOF
cupsfilter /tmp/recibo.txt > /tmp/recibo.pdf 2>/dev/null

curl -s -X POST "$API/documents" -H "X-API-Key: adm-key" \
  -F "file=@/tmp/recibo.pdf;type=application/pdf" \
  -F "caseId=<PEGA_AQUI_EL_CASE_ID>"
```

Tras ~20-60 s, consulta el veredicto:

```bash
curl -s "$API/cases/<CASE_ID>/documents" -H "X-API-Key: adm-key"
```

| Qué probar | Cambia en el recibo | Veredicto esperado |
|---|---|---|
| Comprobante legítimo | importe = el de la transacción | `coincide` |
| **Comprobante falso** | importe muy distinto (p. ej. `50000.00`) | `discrepa` |
| Fecha desfasada | fecha con más de 3 días de diferencia | `discrepa` |
| Documento ilegible | sube un PDF en blanco | `ilegible` |

El campo `verificationSummary` explica el porqué en lenguaje legible.

> El **nombre del comercio no afecta al veredicto** y es intencionado: la
> transacción guarda un identificador opaco (`m1`), no un nombre comercial. Si
> contara, cualquier ticket real daría `discrepa`.

---

## Prueba 4 · Seguir una petición de punta a punta (trazas)

Cada línea de log lleva el mismo `trace_id` desde la API hasta el worker, a
través de la cola. En el portal: **Log Analytics → `log-centinela-dev-sp5x1`**:

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| extend trace = extract('trace=([0-9a-f]{32})', 1, Log_s)
| where isnotempty(trace)
| summarize contenedores = make_set(ContainerAppName_s) by trace
| where array_length(contenedores) > 1
```

Los `trace` que salgan aparecen en **ambos contenedores**: eso solo puede pasar
si el contexto cruzó la cola. Coge uno y sigue su recorrido completo:

```kql
ContainerAppConsoleLogs_CL
| where Log_s has "PEGA_AQUI_EL_TRACE_ID"
| project TimeGenerated, ContainerAppName_s, Log_s
| order by TimeGenerated asc
```

> Las trazas **no** se ven en el portal de Application Insights: el agente OTel
> gestionado de Container Apps no las acepta. Ver `docs/observability.md` §5b.

---

## Prueba 5 · Escalado automático

```bash
# Estado en reposo: deberia dar 0
az containerapp replica list -g rg-centinela-dev \
  -n ca-centinela-worker-dev-sp5x1 --query "length(@)" -o tsv

# Lanza varias transacciones y vuelve a mirar en ~30-60 s: KEDA levanta replicas
# segun la longitud de la cola, hasta 3.
```

Tras unos minutos sin trabajo vuelve solo a 0. Ese ciclo completo
—0 → N → 0— es el entregable de escalado de la Fase 1.

---

## Si algo falla

```bash
# Salud y adaptadores realmente cableados (cosmos/casesDb/queue en true)
curl "$API/health/ready"

# Logs del worker (si esta a 0 replicas, no hay logs: lanza antes una transaccion)
az containerapp logs show -g rg-centinela-dev -n ca-centinela-worker-dev-sp5x1 --follow

# Volver al despliegue anterior si hiciera falta
az webapp start -g rg-centinela-dev -n app-centinela-dev-sp5x1
az functionapp start -g rg-centinela-dev -n func-centinela-dev-sp5x1
```

`/health/ready` es el diagnóstico más útil: si algún adaptador sale en `false`,
el contenedor cayó a los adaptadores en memoria por falta de configuración y
procesará sin persistir nada.
