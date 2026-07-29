# Punto de control — Sistema FUNCIONAL (antes de la Fase 1 / Sprint 6)

**Fecha:** 2026-07-29
**Estado:** ✅ **FUNCIONAL end-to-end.** El sistema completo está desplegado en Azure
y validado. Este documento deja constancia del estado bueno conocido **antes** de
contenedorizar (Fase 1 del Sprint 6), para poder devolverse si algo se rompe.

## Ancla de retorno (rollback)
- **Commit / tag:** `git tag pre-sprint6-funcional` (apunta al commit de este checkpoint).
- **Volver al código:** `git checkout pre-sprint6-funcional` (o `git reset --hard pre-sprint6-funcional` en una rama de rescate).
- **Rama:** `fix/sprint6-fase0` (fixes de despliegue) — pendiente de merge a `develop`.

## Qué funciona (validado en vivo)
Flujo completo verificado sobre Azure:
`POST /transactions` (202) → worker `score_transaction` → cola `cases` → `persist_case`
→ PostgreSQL → `GET /cases` → la consola muestra el caso con su explicación.

- **Evidencia:** 2 casos creados **automáticamente** (cuentas `acc-555` y `acc-777`),
  score **50/50**, reglas `atypical_amount` + `risky_merchant`, estado `Abierto`.
- **Consola** (Next.js, local) leyendo casos reales desde la API de Azure por su BFF
  (la API key nunca llega al navegador).
- **Pruebas:** 104 backend + 22 frontend, en verde.

## Infraestructura desplegada (estado bueno conocido)
- **Resource Group:** `rg-centinela-dev`   **SUFFIX:** `sp5x1`
- **API (App Service):** https://app-centinela-dev-sp5x1.azurewebsites.net
- **Worker (Azure Functions):** `func-centinela-dev-sp5x1` (`score_transaction`, `persist_case`)
- **Cosmos DB:** `cosmos-centinela-dev-sp5x1` (eastus2) — historial + scores
- **PostgreSQL:** `psql-centinela-dev-sp5x1` (**centralus**) — base `centinela_cases`, 7 tablas + estados sembrados
- **Key Vault:** `kv-centinela-dev-sp5x1`   **Storage:** `stcentineladevsp5x1`
- **Auth:** `AUTH_ENABLED=true`. Claves (rol): `svc-key` (servicio), `adm-key` (administrador).
  Los secretos viven en Key Vault (`api-keys`, `cosmos-db-key`, `cases-db-dsn`, `db-admin-password`); **no** en el repo ni en este documento.

## Cómo re-verificar que funciona
```bash
API=https://app-centinela-dev-sp5x1.azurewebsites.net
# 1) enviar una transacción de fraude
curl -s -w '\n%{http_code}\n' -X POST "$API/transactions" \
  -H "X-API-Key: adm-key" -H "Content-Type: application/json" \
  -d '{"transactionId":"'"$(uuidgen)"'","accountId":"acc-demo","amount":"2000000","currency":"COP","merchantId":"m1","merchantCategory":"crypto","latitude":"4.7110","longitude":"-74.0721"}'
# 2) esperar ~90s al worker y listar casos
sleep 90
curl -s "$API/cases?pageSize=10" -H "X-API-Key: adm-key"
```

## Cómo re-desplegar desde cero (scripts ya endurecidos)
```bash
az login
export SUFFIX=sp5x1
export DB_ADMIN_PASS='<la de Key Vault: db-admin-password>'
bash infra/deploy-all.sh
# aplicar el DDL de casos (requiere puerto 5432 alcanzable; la regla de firewall
# del desplegador ya la crea el script con la sintaxis corregida)
```

## Advertencia sobre la Fase 1
La Fase 1 del Sprint 6 **cambia la plataforma de cómputo**: la API de ingesta y el
motor de scoring pasan de App Service / Azure Functions a **contenedores en Azure
Container Apps**. Este checkpoint es el estado **anterior** a ese cambio. Si la
contenedorización o el escalado fallan, este es el punto de retorno seguro.

> Recordatorio de costos: los recursos anteriores siguen encendidos y **consumen
> crédito**. Apagar con `bash infra/destroy.sh` cuando no se estén usando.
