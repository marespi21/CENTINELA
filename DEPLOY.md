# Levantar CENTINELA desde cero

Guía paso a paso para tumbar todo y volver a desplegarlo. Escrita después de
hacerlo de verdad: cada aviso corresponde a un fallo que ocurrió, no a una
precaución teórica.

**Tiempo total: 40-60 minutos**, la mayor parte esperando a Azure.

---

## 0. Prerrequisitos

```bash
az login
az account show          # confirma que es la suscripción correcta
```

| Herramienta | Para qué | Comprobar |
|---|---|---|
| `az` | todo el despliegue | `az version` |
| `docker` | verificar que las imágenes existen antes de desplegar | `docker info` |
| `psql` | aplicar el esquema de la base de casos | `psql --version` |
| `python3` | parchear las especificaciones de Container Apps | `python3 --version` |

Extensiones de `az` (los scripts las instalan solas, pero por si acaso):

```bash
az extension add --name containerapp
az extension add --name application-insights
az extension add --name log-analytics
```

---

## 1. Tumbar todo

```bash
export SUFFIX=sp5x1
bash infra/destroy.sh     # pide escribir el nombre del RG para confirmar
```

Borra el **grupo de recursos entero**. Es asíncrono; tarda 10-20 minutos en
completarse por dentro aunque el comando vuelva enseguida.

```bash
# Esperar a que desaparezca de verdad antes de recrear
until ! az group show --name rg-centinela-dev &>/dev/null; do
  echo "aún borrando..."; sleep 30
done
echo "grupo eliminado"
```

> **No recrees antes de que termine.** Si lanzas el despliegue con el borrado a
> medias, algunos nombres siguen ocupados y fallan con errores confusos.

### Lo que NO borra

- Las **imágenes en GHCR** — viven en GitHub, no en Azure. Se reutilizan.
- El **código** y los secretos que estén fuera de Key Vault.

### Nombres únicos globales

Key Vault, Storage, Cosmos y PostgreSQL usan nombres únicos en todo Azure, y
Key Vault además queda en *soft-delete* unos días tras borrarlo. Si al recrear
falla por nombre ocupado, cambia el sufijo:

```bash
export SUFFIX=sp5x2     # cualquier valor corto y único
```

---

## 2. Infraestructura base

```bash
export SUFFIX=sp5x1
export DB_ADMIN_PASS='<inventa una contraseña fuerte>'   # ¡guárdala!
bash infra/deploy-all.sh
```

Crea Storage y colas, Cosmos, PostgreSQL, Key Vault con los secretos, y la Web
App y Function App antiguas. **Tarda 15-25 minutos**, sobre todo por PostgreSQL.

> El despliegue antiguo (App Service + Function App) se crea porque el script
> lo incluye. Es el punto de retorno del checkpoint. Puedes pararlos después
> (paso 8), pero **la Function App hay que pararla sí o sí**: consume las mismas
> colas que el worker contenedorizado y competirían por los mensajes.

---

## 3. Imágenes en GHCR

Las tres imágenes las construye el pipeline en cada push a `backend/**` o
`frontend/**`. Comprueba que existen y son **públicas**:

```bash
TAG=sha-$(git rev-parse --short=7 HEAD)
for img in api worker console; do
  docker manifest inspect ghcr.io/marespi21/centinela-$img:$TAG >/dev/null 2>&1 \
    && echo "$img OK" || echo "$img NO disponible"
done
```

**Si alguna da error**, es por una de dos cosas:

1. **El paquete es privado.** GHCR los crea privados por defecto. Hay que
   marcarlos públicos a mano, y **solo puede hacerlo el propietario del
   repositorio (`marespi21`)**:
   `github.com/marespi21/CENTINELA` → *Packages* → cada paquete →
   *Package settings* → *Change visibility* → **Public**.
2. **El pipeline no ha construido ese commit.** Míralo en la pestaña *Actions*.

> **`latest` NO existe** fuera de la rama por defecto. Desplegando desde una
> rama de trabajo hay que indicar `sha-xxxxxxx` explícitamente, o el despliegue
> crea una revisión que nunca arranca porque no puede hacer *pull*.

---

## 4. Container Apps — primera pasada

```bash
export SUFFIX=sp5x1
export IMAGE_TAG=sha-xxxxxxx     # el que comprobaste arriba
bash infra/containerapps.sh
```

Crea identidad gestionada, RBAC, Log Analytics, el entorno, y las tres apps
(API, worker, consola) con sondas y reglas de escalado. **10-15 minutos**, casi
todo creando el entorno.

### Si falla con `AKSCapacityHeavyUsage`

Los entornos de Container Apps corren sobre AKS y heredan su falta de capacidad.
Pasó con `eastus`. Cambia de región y **borra el entorno a medias antes de
reintentar** — si no, el script lo encuentra y lo da por bueno:

```bash
az containerapp env delete -g rg-centinela-dev -n cae-centinela-dev-sp5x1 --yes
export ACA_LOCATION=eastus2      # o westus2, centralus...
bash infra/containerapps.sh
```

El script ya detecta un entorno en mal estado y aborta diciéndote esto mismo.

---

## 5. OCR (Document Intelligence F0)

```bash
bash infra/document-intelligence.sh
```

> **El orden importa.** Este script concede permisos a la identidad gestionada
> que crea el paso 4, así que **tiene que ir después**. Si lo lanzas antes, avisa
> de que la identidad no existe y no asigna el rol — el OCR fallaría con error de
> autenticación.

Azure permite **una sola instancia F0 de Document Intelligence por
suscripción**. Si ya existe una de un despliegue anterior, reutilízala:

```bash
export DOC_INTELLIGENCE=<nombre-de-la-existente>
```

---

## 6. Esquema de la base de casos

```bash
# Permitir tu IP en el firewall de PostgreSQL
MYIP=$(curl -s ifconfig.me)
az postgres flexible-server firewall-rule create \
  -g rg-centinela-dev --server-name psql-centinela-dev-sp5x1 \
  --name allow-deployer --start-ip-address "$MYIP" --end-ip-address "$MYIP"

# Aplicar el esquema
export CASES_DB_DSN=$(az keyvault secret show \
  --vault-name kv-centinela-dev-sp5x1 --name cases-db-dsn --query value -o tsv)
psql "$CASES_DB_DSN" -f scripts/init-cases-db.sql
```

En un despliegue **desde cero** usa `init-cases-db.sql`, que ya incluye las
columnas de verificación documental.

Sobre una base **ya existente**, usa solo la migración — el script completo
recrea los triggers de inmutabilidad de la auditoría (`DROP` + `CREATE`),
abriendo una ventana breve sin protección anti-manipulación:

```bash
psql "$CASES_DB_DSN" -f scripts/migrations/2026-07-29-verificacion-documental.sql
```

---

## 7. Container Apps — segunda pasada

```bash
bash infra/containerapps.sh
```

**Sí, otra vez.** El paso 5 creó el recurso de OCR; esta pasada inyecta su
endpoint en el worker. Sin ella el worker registra los documentos pero no los
verifica (usa el analizador nulo y todo sale `ilegible`).

Los scripts son idempotentes: re-ejecutarlos no rompe nada.

---

## 8. Observabilidad y limpieza

```bash
export ALERT_EMAIL=tu@correo
bash infra/observability.sh

# Parar el despliegue antiguo: la Function App COMPITE por las mismas colas
az functionapp stop -g rg-centinela-dev -n func-centinela-dev-sp5x1
az webapp stop -g rg-centinela-dev -n app-centinela-dev-sp5x1
```

> El App Service es plan **F1 (gratuito) y Azure lo vuelve a levantar solo**.
> Si te molesta que reaparezca, bórralo en vez de pararlo:
> `az webapp delete -g rg-centinela-dev -n app-centinela-dev-sp5x1`

---

## 9. Verificar

```bash
API=$(az containerapp show -g rg-centinela-dev -n ca-centinela-api-dev-sp5x1 \
        --query properties.configuration.ingress.fqdn -o tsv)
CONSOLA=$(az containerapp show -g rg-centinela-dev -n ca-centinela-console-dev-sp5x1 \
        --query properties.configuration.ingress.fqdn -o tsv)
echo "API:     https://$API"
echo "Consola: https://$CONSOLA"

# 1. Los adaptadores REALES tienen que salir en true.
#    Si alguno sale false, el contenedor cayó a los adaptadores en memoria
#    por falta de configuración y procesará sin persistir nada.
curl -s "https://$API/health/ready"

# 2. Flujo completo: transacción -> caso
curl -s -X POST "https://$API/transactions" \
  -H "X-API-Key: adm-key" -H "Content-Type: application/json" \
  -d '{"transactionId":"'"$(uuidgen)"'","accountId":"acc-verificacion",
       "amount":"3000000","currency":"COP","merchantId":"m1",
       "merchantCategory":"crypto","latitude":"4.7110","longitude":"-74.0721"}'

sleep 90    # KEDA despierta el worker desde cero réplicas
curl -s "https://$API/cases?pageSize=5" -H "X-API-Key: adm-key"
```

El caso debe aparecer con `score 50` y estado `Abierto`. Abre la consola en el
navegador y compruébalo también ahí.

Pruebas más completas —OCR en ambas direcciones, seguimiento de trazas,
escalado— en [`docs/pruebas-despliegue.md`](docs/pruebas-despliegue.md).

---

## Resumen: todos los comandos seguidos

```bash
az login
export SUFFIX=sp5x1
export DB_ADMIN_PASS='<contraseña fuerte>'
export IMAGE_TAG=sha-xxxxxxx
export ALERT_EMAIL=tu@correo

bash infra/destroy.sh
until ! az group show --name rg-centinela-dev &>/dev/null; do sleep 30; done

bash infra/deploy-all.sh
bash infra/containerapps.sh
bash infra/document-intelligence.sh

MYIP=$(curl -s ifconfig.me)
az postgres flexible-server firewall-rule create \
  -g rg-centinela-dev --server-name psql-centinela-dev-sp5x1 \
  --name allow-deployer --start-ip-address "$MYIP" --end-ip-address "$MYIP"
export CASES_DB_DSN=$(az keyvault secret show \
  --vault-name kv-centinela-dev-sp5x1 --name cases-db-dsn --query value -o tsv)
psql "$CASES_DB_DSN" -f scripts/init-cases-db.sql

bash infra/containerapps.sh          # segunda pasada: cablea el OCR
bash infra/observability.sh

az functionapp stop -g rg-centinela-dev -n func-centinela-dev-sp5x1
az webapp stop -g rg-centinela-dev -n app-centinela-dev-sp5x1
```

---

## Problemas conocidos

| Síntoma | Causa | Solución |
|---|---|---|
| `RetentionInDays doesn't match the SKU limits` | La SKU `PerGB2018` exige 30 días mínimo | Ya corregido en el script |
| `AKSCapacityHeavyUsage` | La región no tiene capacidad | Borra el entorno y cambia `ACA_LOCATION` |
| Revisión que nunca arranca | La etiqueta de imagen no existe (`latest` fuera de la rama por defecto) | `export IMAGE_TAG=sha-xxxxxxx` |
| Documentos siempre `ilegible` | El worker no tiene el endpoint del OCR | Ejecuta el paso 7 (segunda pasada) |
| `/health/ready` con algún adaptador en `false` | Falta configuración; cayó a adaptadores en memoria | Revisa Key Vault y re-ejecuta el paso 4 |
| Trazas ausentes en Application Insights | El agente OTel gestionado no las acepta | Conocido; ver `docs/observability.md` §5b. Las trazas se siguen por `trace_id` en los logs |
| El App Service vuelve a arrancar solo | Plan F1 gratuito | Bórralo en vez de pararlo |

---

## Coste

| Recurso | Coste |
|---|---|
| **PostgreSQL B1ms** | El único caro: encendido 24/7. Se puede parar hasta 7 días con `az postgres flexible-server stop`, pero el sistema deja de funcionar |
| Container Apps | ~0 con escalado a cero (180 000 vCPU-s/mes gratis) |
| Document Intelligence F0 | 0 (500 páginas/mes) |
| Log Analytics | 0 hasta 5 GB/mes |
| Cosmos DB | 0 si es la cuenta con free tier de la suscripción |
| GHCR | 0 (paquetes públicos) |

Apagar todo: `bash infra/destroy.sh`.
