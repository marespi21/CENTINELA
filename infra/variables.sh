#!/usr/bin/env bash
# Variables compartidas de infraestructura CENTINELA.
# Todos los scripts deben sourcear este archivo. No hardcodear nombres.

set -euo pipefail

PROJECT=centinela
ENV=dev
LOCATION=eastus
# App Service: eastus sin cuota en esta suscripción; centralus sí permite F1
APP_LOCATION=centralus

RESOURCE_GROUP=rg-${PROJECT}-${ENV}
APP_SERVICE_PLAN=plan-${PROJECT}-${ENV}
WEBAPP=app-${PROJECT}-${ENV}
STORAGE_ACCOUNT=st${PROJECT}${ENV}

QUEUE_NAME=transactions
DOCUMENTS_QUEUE=documents
BLOB_CONTAINER=documents

# App Service SKU (F1 = Free; B1+ requiere cuota y es necesario para VNet integration)
APP_SERVICE_SKU=F1

# Red (integración con Juanjo). Nombres compartidos por deploy-network.sh.
VNET=vnet-${PROJECT}-${ENV}
SUBNET_APP=subnet-app
SUBNET_DATA=subnet-data

# Seguridad (módulo Lukas). Nombre de Key Vault: 3-24, único global.
KEY_VAULT=kv-${PROJECT}-${ENV}

# Budget / costos (módulo Chanti)
BUDGET_NAME=budget-${PROJECT}-${ENV}
BUDGET_AMOUNT=50
BUDGET_ALERT_EMAIL=${BUDGET_ALERT_EMAIL:-team@example.com}

# Almacén NoSQL de transacciones — Cosmos DB SQL API (módulo Chanti, semana 2)
# El nombre de la cuenta es único global (3-44, minúsculas, dígitos y guiones).
COSMOS_ACCOUNT=cosmos-${PROJECT}-${ENV}
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

# Alias usados por scripts legacy / mensajes
PROJECT_NAME="${PROJECT}"
ENVIRONMENT="${ENV}"
