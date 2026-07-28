# Guía de despliegue end-to-end — CENTINELA (Semana 4, integración)

Levanta **todo** el sistema en Azure de una sola corrida y valida el flujo de
fraude completo: transacción → scoring → caso → lectura por la API.

## 1. Prerrequisitos
- `az login` con una suscripción con rol **Owner** (o Contributor + User Access
  Administrator, para asignar roles RBAC).
- **Azure Functions Core Tools v4** (`func`) para publicar el worker.
- `zip`, `curl`, `openssl`, `psql`.

## 2. Despliegue en un comando
```bash
export SUFFIX=ab12cd          # sufijo único para nombres globales (recomendado)
# Opcional: exporta secretos reales; si no, se generan para la demo.
#   export API_KEYS="svc-key:servicio,adm-key:administrador,ana-key:analista"
bash infra/deploy-all.sh
```
El orquestador ([`infra/deploy-all.sh`](../infra/deploy-all.sh)) hace, en orden:
infra base + Key Vault + Cosmos → PostgreSQL → Function App → secretos por
referencia ([`security.sh`](../infra/security.sh)) → app settings + deploy de la
API y el worker. Al terminar imprime la URL de la API.

> **Nota de red:** para la demo end-to-end con App Service **F1**, PostgreSQL se
> crea **público con firewall** (F1 no integra VNet). El diseño de **producción**
> es privado (`deploy-cases-db.sh` sobre VNet + App Service B1+).

## 3. Validación de cierre (evidencia)

Sustituye `APP` por tu Web App (`app-centinela-dev-<suffix>`).

**a) Enviar una transacción de fraude** (monto alto + categoría de riesgo → abre caso):
```bash
curl -s -w '\nHTTP %{http_code}\n' -X POST https://APP.azurewebsites.net/transactions \
  -H "X-API-Key: adm-key" -H "Content-Type: application/json" \
  -d '{"transactionId":"'"$(uuidgen)"'","accountId":"acc-999","amount":"2000000","currency":"COP","merchantId":"m1","merchantCategory":"crypto","latitude":"4.7110","longitude":"-74.0721"}'
```
Esperado: **HTTP 202** (la API la aceptó y encoló).

**b) Esperar al worker** (~1 min por el arranque en frío):
```bash
sleep 60
```

**c) Obtener el id del caso creado** (desde PostgreSQL):
```bash
CASE_ID=$(psql "$CASES_DB_DSN" -t -A -c "SELECT id FROM casos ORDER BY creado_en DESC LIMIT 1;")
echo "Caso: $CASE_ID"
```

**d) Leer el caso por la API** (con rol analista → 200 con explicación):
```bash
curl -s -w '\nHTTP %{http_code}\n' -H "X-API-Key: ana-key" \
  "https://APP.azurewebsites.net/cases/$CASE_ID"
```
Esperado: **HTTP 200** con el caso, su **explicación** (`isCase`, `reasons`,
`summary`) y su traza de auditoría. → **Evidencia del flujo completo.**

## 4. Prueba de aislamiento
- **Contenedor de documentos:** privado. Sin credenciales, la URL directa del
  blob responde `PublicAccessNotPermitted` / `404`:
  ```bash
  curl -s -o /dev/null -w "%{http_code}\n" \
    "https://stcentineladev<suffix>.blob.core.windows.net/documents/x.pdf"
  ```
- **PostgreSQL (producción):** con el script privado queda inalcanzable desde
  internet (VNet + `Public Network Access=Disabled`). En modo demo es público con
  firewall; documentar la diferencia como decisión de la demo.

## 5. Reporte de crédito consumido
```bash
az consumption usage list --top 20 -o table 2>/dev/null || \
  echo "Ver costo en el portal: Cost Management + Billing (RG rg-centinela-dev)."
```
El proyecto deja una **alerta de presupuesto** configurada (ver `infra/budget.sh`,
umbral 50 USD).

## 6. Apagar todo (detener el gasto)
```bash
bash infra/destroy.sh   # escribe el nombre del RG para confirmar
```

## Checklist de aceptación (DoD)
- [ ] `deploy-all.sh` levanta todo sin pasos manuales (Function App incluida).
- [ ] Transacción de fraude → caso consultable por `GET /cases/{id}` con explicación.
- [ ] Evidencia de aislamiento (contenedor privado) y reporte de crédito.
- [ ] Secretos por referencia a Key Vault (`bash infra/verify_secrets.sh`).
