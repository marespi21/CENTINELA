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
BLOB_CONTAINER=documents

# App Service SKU (F1 = Free; B1 requiere cuota de cómputo)
APP_SERVICE_SKU=F1

# Red (integración con Juanjo)
VNET=vnet-${PROJECT}-${ENV}
SUBNET_APP=subnet-app
SUBNET_DATA=subnet-data

# Alias usados por scripts legacy / mensajes
PROJECT_NAME="${PROJECT}"
ENVIRONMENT="${ENV}"
