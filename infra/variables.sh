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

# Alias usados por scripts legacy / mensajes
PROJECT_NAME="${PROJECT}"
ENVIRONMENT="${ENV}"
