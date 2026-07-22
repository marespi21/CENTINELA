# README - Networking (Proyecto Centinela)

Propósito
- Este README explica qué se implementó, qué conceptos debes entender, cómo probar lo que implementaste y cómo compartirlo con el equipo en GitHub.

Resumen de lo implementado
- VNet: `Centinela-VNet` (10.0.0.0/16)
- Subnet-App: `10.0.1.0/24`
- Subnet-Storage: `10.0.2.0/24`
- NSG: `NSG-Centinela-Storage` aplicado a `Subnet-Storage` con reglas:
  - `Allow-App-To-Storage` (priority 100): permite desde `10.0.1.0/24` hacia `10.0.2.0/24`.
  - `Deny-Internet-To-Storage` (priority 200): deniega desde `Internet` hacia `10.0.2.0/24`.
- Log Analytics: `Centinela-LogAnalytics` y diagnostic settings del NSG configurados.
- Tags aplicadas: `Project=Centinela`, `Environment=dev`.

Conceptos clave para estudiar (prioridad alta → baja)
- Azure Virtual Networks (VNet) y subredes: direccionamiento IP, prefijos, y límites.
- Network Security Groups (NSG): reglas, prioridad (número menor = mayor prioridad), direction (Inbound/Outbound), alcance (aplicado a subnet o NIC).
- Reglas por defecto vs reglas definidas: las reglas creadas con prioridad menor se evalúan primero.
- Network Watcher y diagnósticos: Log Analytics, diagnostic settings y cómo recibir eventos y counters.
- NSG Flow Logs vs Virtual Network Flow Logs: estado de retiro de NSG Flow Logs y por qué migrar.
- Azure CLI básico: `az login`, `az account set`, `az network ...`, `az vm ...`, y cómo leer outputs JSON/TSV.
- ARM (Azure Resource Manager): plantillas, despliegues y mensajes comunes de error (ej. SkuNotAvailable).

Cómo compartir tu trabajo con el equipo (pasos prácticos)
1. Crea una rama local:
   - `git checkout -b feat/networking-week1` 
2. Asegúrate de incluir el archivo de documentación que resume tu trabajo: `docs/networking-week1.md` y este `README_NETWORKING.md`.
   - `git add docs/networking-week1.md README_NETWORKING.md`
   - `git commit -m "feat(networking): add Week1 network config and README"`
3. Push y PR:
   - `git push origin feat/networking-week1`
   - Abre un Pull Request en GitHub hacia `main` o la rama de integración, agrega reviewers y descripción con: objetivo, cambios y comandos para reproducir.
4. Para que otros revisen y prueben localmente:
   - `git clone <repo-url>`
   - `git checkout feat/networking-week1`
   - Revisar `docs/networking-week1.md` y este README.

Cómo verificar (comandos rápidos)
- Mostrar VNet y subnets:
  - `az network vnet show -g NetworkWatcherRG -n Centinela-VNet -o table`
  - `az network vnet subnet show -g NetworkWatcherRG --vnet-name Centinela-VNet -n Subnet-Storage -o json`
- Mostrar NSG y reglas:
  - `az network nsg show -g NetworkWatcherRG -n NSG-Centinela-Storage -o json`
  - `az network nsg rule list -g NetworkWatcherRG --nsg-name NSG-Centinela-Storage -o table`
- Mostrar Log Analytics workspace:
  - `az monitor log-analytics workspace show -g NetworkWatcherRG -n Centinela-LogAnalytics -o table`
- Consultar diagnostic settings del NSG:
  - `NSG_ID=$(az network nsg show -g NetworkWatcherRG -n NSG-Centinela-Storage --query id -o tsv)`
  - `az monitor diagnostic-settings list --resource $NSG_ID -o json`

Cómo probar la parte que hiciste (prueba con VMs — genera coste)
Nota: usar otra región si `mexicocentral` no tiene capacidad (ej. `eastus`).

1) Crear recursos de prueba (ejemplo `eastus`):
```bash
RG=NetworkWatcherRG
LOC=eastus
VNET=Centinela-Test-VNet
NSG=NSG-Centinela-Storage-test

# Crear VNet y subnets (prueba separada de la VNet de producción)
az network vnet create -g $RG -n $VNET --address-prefix 10.20.0.0/16 --subnet-name Subnet-App --subnet-prefix 10.20.1.0/24 -l $LOC
az network vnet subnet create -g $RG --vnet-name $VNET -n Subnet-Storage --address-prefix 10.20.2.0/24

# Crear NSG de prueba y reglas (mismas reglas lógicas)
az network nsg create -g $RG -n $NSG -l $LOC
az network nsg rule create -g $RG --nsg-name $NSG -n Allow-App-To-Storage --priority 100 --direction Inbound --access Allow --source-address-prefix 10.20.1.0/24 --destination-address-prefix 10.20.2.0/24 --protocol '*' --source-port-range '*' --destination-port-range '*'
az network nsg rule create -g $RG --nsg-name $NSG -n Deny-Internet-To-Storage --priority 200 --direction Inbound --access Deny --source-address-prefix Internet --destination-address-prefix 10.20.2.0/24 --protocol '*' --source-port-range '*' --destination-port-range '*'
az network vnet subnet update -g $RG --vnet-name $VNET -n Subnet-Storage --network-security-group $NSG

# Crear dos VMs de prueba (vm-app sin IP pública, vm-storage con IP pública)
az vm create -g $RG -n vm-app-test --image Canonical:UbuntuServer:22_04-lts:latest --size Standard_B1ms --vnet-name $VNET --subnet Subnet-App --public-ip-address "" --generate-ssh-keys -l $LOC
az vm create -g $RG -n vm-storage-test --image Canonical:UbuntuServer:22_04-lts:latest --size Standard_B1ms --vnet-name $VNET --subnet Subnet-Storage --generate-ssh-keys -l $LOC

# Obtener IPs
az vm list-ip-addresses -g $RG -n vm-storage-test -o table

# Desde vm-app-test (usando run-command) probar conexión a puerto 22 de la IP privada de vm-storage-test
STORAGE_PRIVATE=$(az vm list-ip-addresses -g $RG -n vm-storage-test --query "[0].virtualMachine.network.privateIpAddresses[0]" -o tsv)
az vm run-command invoke -g $RG -n vm-app-test --command-id RunShellScript --scripts "apt-get update && apt-get install -y netcat-openbsd && nc -vz $STORAGE_PRIVATE 22"

# Desde Internet: verificar la IP pública de vm-storage-test (esperamos DENY para acceso entrante desde Internet)
STORAGE_PUBLIC=$(az vm list-ip-addresses -g $RG -n vm-storage-test --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
nc -vz $STORAGE_PUBLIC 22 || echo "Conexión entrante denegada (esperado)"
```

2) Limpieza tras la prueba:
```bash
az vm delete -g $RG -n vm-app-test --yes
az vm delete -g $RG -n vm-storage-test --yes
az network public-ip list -g $RG -o table  # eliminar IPs públicas si quedan
az network nsg delete -g $RG -n $NSG
az network vnet delete -g $RG -n $VNET
```

Alternativa sin crear VMs (comprobación lógica y logs)
- Usar los comandos del apartado "Cómo verificar" y revisar en el Portal → Log Analytics los eventos `NetworkSecurityGroupEvent` y `NetworkSecurityGroupRuleCounter`.

Preguntas frecuentes rápidas
- ¿Puedo cambiar la regla para permitir sólo ciertos puertos? Sí: en la regla NSG cambia `destination-port-range` (ej. `80` o `443`).
- ¿Cómo veo si una regla está bloqueando un IP concreta? Revisa `NSG` en Portal o consulta `AzureDiagnostics` en Log Analytics.

Soporte y próximos pasos
- Si quieres, puedo: (A) crear un branch y abrir un PR con la documentación; (B) desplegar VMs de verificación en `eastus`; (C) preparar un breve slide o mensaje para el equipo.

Archivo de referencia ya guardado: `docs/networking-week1.md` (resumen técnico)
