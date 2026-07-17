#!/usr/bin/env bash
# Variables compartidas de infraestructura CENTINELA.
# Sobrescribir en el entorno o en un archivo local no versionado.

set -euo pipefail

export PROJECT_NAME="${PROJECT_NAME:-centinela}"
export ENVIRONMENT="${ENVIRONMENT:-dev}"
export LOCATION="${LOCATION:-eastus}"
export RESOURCE_GROUP="${RESOURCE_GROUP:-rg-${PROJECT_NAME}-${ENVIRONMENT}}"
export SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-}"
