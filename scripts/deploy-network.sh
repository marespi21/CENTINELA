#!/usr/bin/env bash
# Networking (módulo Juanjo): VNet + subnets + NSG + reglas + Log Analytics.
# Usa los nombres compartidos de infra/variables.sh para integrarse con
# deploy.sh y private-network.sh. Acepta --location para override.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../infra/variables.sh
source "${SCRIPT_DIR}/../infra/variables.sh"

RG="${RESOURCE_GROUP}"
LOC="${LOCATION}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group) RG="$2"; shift 2;;
    --location) LOC="$2"; shift 2;;
    *) echo "Unknown arg $1"; exit 1;;
  esac
done

az group create -n "$RG" -l "$LOC" --output none

# VNet + subnet de la app (delegada a Microsoft.Web para VNet integration)
az network vnet create -g "$RG" -n "${VNET}" --address-prefix 10.0.0.0/16 \
  --subnet-name "${SUBNET_APP}" --subnet-prefix 10.0.1.0/24 -l "$LOC"
az network vnet subnet update -g "$RG" --vnet-name "${VNET}" -n "${SUBNET_APP}" \
  --delegations Microsoft.Web/serverFarms || true

# Subnet de datos (storage / private endpoints)
az network vnet subnet create -g "$RG" --vnet-name "${VNET}" -n "${SUBNET_DATA}" \
  --address-prefixes 10.0.2.0/24

# NSG de la subnet de datos: solo la app entra, Internet no
az network nsg create -g "$RG" -n NSG-Centinela-Storage -l "$LOC"
az network nsg rule create -g "$RG" --nsg-name NSG-Centinela-Storage --name Allow-App-To-Storage \
  --priority 100 --direction Inbound --access Allow \
  --source-address-prefix 10.0.1.0/24 --destination-address-prefix 10.0.2.0/24 || true
az network nsg rule create -g "$RG" --nsg-name NSG-Centinela-Storage --name Deny-Internet-To-Storage \
  --priority 200 --direction Inbound --access Deny \
  --source-address-prefix Internet --destination-address-prefix 10.0.2.0/24 || true
az network vnet subnet update -g "$RG" --vnet-name "${VNET}" -n "${SUBNET_DATA}" \
  --network-security-group NSG-Centinela-Storage

# Observabilidad de red (Log Analytics + diagnostic settings del NSG)
az monitor log-analytics workspace create -g "$RG" -n Centinela-LogAnalytics -l "$LOC" --sku PerGB2018 || true
NSG_ID=$(az network nsg show -g "$RG" -n NSG-Centinela-Storage --query id -o tsv)
WORKSPACE_ID=$(az monitor log-analytics workspace show -g "$RG" -n Centinela-LogAnalytics --query id -o tsv)
az monitor diagnostic-settings create --name diag-NSG-Centinela --resource "$NSG_ID" --workspace "$WORKSPACE_ID" \
  --logs '[{"category":"NetworkSecurityGroupEvent","enabled":true},{"category":"NetworkSecurityGroupRuleCounter","enabled":true}]' || true

az resource tag --ids "$(az network vnet show -g "$RG" -n "${VNET}" --query id -o tsv)" --tags Project=Centinela Environment="${ENV}" || true
az resource tag --ids "$NSG_ID" --tags Project=Centinela Environment="${ENV}" || true

echo "Networking listo (VNet ${VNET}, subnets ${SUBNET_APP}/${SUBNET_DATA})"
