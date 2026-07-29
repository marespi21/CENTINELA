#!/usr/bin/env bash
# Variables compartidas de infraestructura CENTINELA.
# Todos los scripts deben sourcear este archivo. No hardcodear nombres.

set -euo pipefail

PROJECT=centinela
ENV=dev
LOCATION=eastus
# App Service: eastus sin cuota en esta suscripción; centralus sí permite F1
APP_LOCATION=centralus

# Sufijo para nombres GLOBALES (storage, web app, key vault, cosmos, function app,
# postgres). Vacío por defecto; exporta uno único si hay colisión de nombre:
#   export SUFFIX=ab12cd
SUFFIX="${SUFFIX:-}"
# Región de Cosmos (eastus suele reportar falta de cupo; eastus2 sí). Configurable.
COSMOS_LOCATION="${COSMOS_LOCATION:-eastus2}"
# Región de PostgreSQL Flexible Server. En suscripciones restringidas (p. ej.
# estudiante) eastus/eastus2 devuelven "location is restricted"; centralus sí
# permite crear el servidor. Configurable.
DB_LOCATION="${DB_LOCATION:-centralus}"

RESOURCE_GROUP=rg-${PROJECT}-${ENV}
APP_SERVICE_PLAN=plan-${PROJECT}-${ENV}
WEBAPP=app-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}
STORAGE_ACCOUNT=st${PROJECT}${ENV}${SUFFIX}
# Function App (worker de scoring + consumidor de casos) — módulo Jorge, semana 4.
FUNCTION_APP=func-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}

QUEUE_NAME=transactions
DOCUMENTS_QUEUE=documents
CASES_QUEUE=cases
BLOB_CONTAINER=documents

# App Service SKU (F1 = Free; B1+ requiere cuota y es necesario para VNet integration)
APP_SERVICE_SKU=F1

# Red (integración con Juanjo). Nombres compartidos por deploy-network.sh.
VNET=vnet-${PROJECT}-${ENV}
SUBNET_APP=subnet-app
SUBNET_DATA=subnet-data
SUBNET_DB=subnet-db


# Seguridad (módulo Lukas). Nombre de Key Vault: 3-24, único global.
KEY_VAULT=kv-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}

# Budget / costos (módulo Chanti)
BUDGET_NAME=budget-${PROJECT}-${ENV}
BUDGET_AMOUNT=50
BUDGET_ALERT_EMAIL=${BUDGET_ALERT_EMAIL:-team@example.com}

# Almacén NoSQL de transacciones — Cosmos DB SQL API (módulo Chanti, semana 2)
# El nombre de la cuenta es único global (3-44, minúsculas, dígitos y guiones).
COSMOS_ACCOUNT=cosmos-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}
COSMOS_DATABASE=centinela
COSMOS_CONTAINER=transactions
# Clave de partición: NO se puede cambiar tras crear el contenedor (ver docs/nosql.md).
COSMOS_PARTITION_KEY=/accountId
# Consistencia: Session equilibra latencia/costo y garantiza read-your-writes.
COSMOS_CONSISTENCY=Session
# Throughput provisionado (RU/s). 400 entra completo en el free tier (1000 RU/s).
COSMOS_THROUGHPUT=400
# TTL por defecto del contenedor (segundos). 90 días ≥ ventana temporal más
# amplia de las reglas de fraude (semana 2). -1 = sin expiración.
COSMOS_TTL_SECONDS=7776000

# Almacén relacional de casos — PostgreSQL Flexible Server (módulo Juan José).
DB_SERVER=psql-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}
DB_NAME=centinela_cases
DB_ADMIN_USER=centinela_admin

# ---------------------------------------------------------------------------
# Contenedores — Sprint 6, Fase 1 (módulo Andrés)
# ---------------------------------------------------------------------------
# Registro de imágenes. GHCR: privado y sin coste (free tier), frente a ACR que
# no tiene capa gratuita. Parametrizado por si hay que migrar a ACR: basta
# cambiar REGISTRY/REGISTRY_NAMESPACE y las credenciales de pull.
REGISTRY="${REGISTRY:-ghcr.io}"
REGISTRY_NAMESPACE="${REGISTRY_NAMESPACE:-marespi21}"
IMAGE_API="${REGISTRY}/${REGISTRY_NAMESPACE}/${PROJECT}-api"
IMAGE_WORKER="${REGISTRY}/${REGISTRY_NAMESPACE}/${PROJECT}-worker"
# Etiqueta a desplegar. Un sha corto es inmutable; `latest` puede cambiar bajo
# los pies de una revisión ya desplegada y romper la reproducibilidad.
IMAGE_TAG="${IMAGE_TAG:-latest}"

# Azure Container Apps. Región con cuota de Container Apps en la suscripción.
ACA_LOCATION="${ACA_LOCATION:-eastus}"
ACA_ENVIRONMENT=cae-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}
ACA_API=ca-${PROJECT}-api-${ENV}${SUFFIX:+-${SUFFIX}}
ACA_WORKER=ca-${PROJECT}-worker-${ENV}${SUFFIX:+-${SUFFIX}}
LOG_WORKSPACE=log-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}
# Identidad gestionada de usuario: la comparten API y worker para leer Key
# Vault, las colas y Cosmos SIN ninguna credencial en la imagen.
ACA_IDENTITY=id-${PROJECT}-${ENV}${SUFFIX:+-${SUFFIX}}

# Recursos por réplica. 0.25 vCPU / 0.5 GiB es el mínimo de Container Apps y el
# que más estira la cuota gratuita mensual.
ACA_CPU="${ACA_CPU:-0.25}"
ACA_MEMORY="${ACA_MEMORY:-0.5Gi}"
# Escalado a cero por defecto: sin tráfico ni mensajes en cola, el gasto es 0.
ACA_API_MIN_REPLICAS="${ACA_API_MIN_REPLICAS:-0}"
ACA_API_MAX_REPLICAS="${ACA_API_MAX_REPLICAS:-3}"
ACA_WORKER_MIN_REPLICAS="${ACA_WORKER_MIN_REPLICAS:-0}"
ACA_WORKER_MAX_REPLICAS="${ACA_WORKER_MAX_REPLICAS:-3}"
# Mensajes en cola por réplica antes de que KEDA añada otra.
ACA_QUEUE_LENGTH="${ACA_QUEUE_LENGTH:-5}"

# Nombres de los secretos ya existentes en Key Vault (los crea security.sh).
KV_SECRET_API_KEYS=api-keys
KV_SECRET_COSMOS_KEY=cosmos-db-key
KV_SECRET_CASES_DSN=cases-db-dsn
# Token de solo-lectura de GHCR para que Container Apps pueda hacer pull de un
# paquete privado. Se guarda en Key Vault; NUNCA en el repo ni en el pipeline.
KV_SECRET_GHCR_TOKEN=ghcr-pull-token

# Alias usados por scripts legacy / mensajes
PROJECT_NAME="${PROJECT}"
ENVIRONMENT="${ENV}"
