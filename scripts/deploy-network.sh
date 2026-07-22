#!/usr/bin/env bash
set -euo pipefail
usage() { echo "Usage: $0 --resource-group RG --location LOC"; exit 1; }
RG=""
LOC="mexicocentral"
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --resource-group) RG="$2"; shift 2;;
    --location) LOC="$2"; shift 2;;
    *) echo "Unknown arg $1"; usage;;
  esac
done
[ -n "$RG" ] || usage

az group create -n "$RG" -l "$LOC"
az network vnet create -g "$RG" -n Centinela-VNet --address-prefix 10.0.0.0/16 --subnet-name Subnet-App --subnet-prefix 10.0.1.0/24 -l "$LOC"
az network vnet subnet create -g "$RG" --vnet-name Centinela-VNet -n Subnet-Storage --address-prefixes 10.0.2.0/24
az network nsg create -g "$RG" -n NSG-Centinela-Storage -l "$LOC"
az network nsg rule create -g "$RG" --nsg-name NSG-Centinela-Storage --name Allow-App-To-Storage --priority 100 --direction Inbound --access Allow --source-address-prefix 10.0.1.0/24 --destination-address-prefix 10.0.2.0/24 || true
az network nsg rule create -g "$RG" --nsg-name NSG-Centinela-Storage --name Deny-Internet-To-Storage --priority 200 --direction Inbound --access Deny --source-address-prefix Internet --destination-address-prefix 10.0.2.0/24 || true
az network vnet subnet update -g "$RG" --vnet-name Centinela-VNet -n Subnet-Storage --network-security-group NSG-Centinela-Storage
az monitor log-analytics workspace create -g "$RG" -n Centinela-LogAnalytics -l "$LOC" --sku PerGB2018 || true
NSG_ID=$(az network nsg show -g "$RG" -n NSG-Centinela-Storage --query id -o tsv)
WORKSPACE_ID=$(az monitor log-analytics workspace show -g "$RG" -n Centinela-LogAnalytics --query id -o tsv)
az monitor diagnostic-settings create --name diag-NSG-Centinela --resource "$NSG_ID" --workspace "$WORKSPACE_ID" --logs '[{"category":"NetworkSecurityGroupEvent","enabled":true},{"category":"NetworkSecurityGroupRuleCounter","enabled":true}]' || true

az resource tag --ids $(az network vnet show -g "$RG" -n Centinela-VNet --query id -o tsv) --tags Project=Centinela Environment=dev || true
az resource tag --ids "$NSG_ID" --tags Project=Centinela Environment=dev || true

echo "Deployment finished"
