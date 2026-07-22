# Networking - Semana 1 (Proyecto Centinela)

Resumen corto
- Propósito: implementar y validar la capa de red y control de acceso para la Semana 1.
- Estado: completado (configuración lógica y telemetría). Pruebas con VMs reales no se dejaron en `mexicocentral` por falta de capacidad.

Recursos creados
- Resource Group: `NetworkWatcherRG` (verificado)
- VNet: `Centinela-VNet` (10.0.0.0/16)
- Subnets: `Subnet-App` (10.0.1.0/24), `Subnet-Storage` (10.0.2.0/24)
- NSG: `NSG-Centinela-Storage`
  - Regla `Allow-App-To-Storage`: fuente `10.0.1.0/24` → destino `10.0.2.0/24`, prioridad `100`, Allow
  - Regla `Deny-Internet-To-Storage`: fuente `Internet` → destino `10.0.2.0/24`, prioridad `200`, Deny
- Log Analytics: `Centinela-LogAnalytics` (diagnósticos de NSG configurados)
- Tags aplicadas: `Project=Centinela`, `Environment=dev` (VNet y NSG)

Comandos útiles (CLI) — verificación y auditoría
- Ver VNet y subnets:
  - `az network vnet show -g NetworkWatcherRG -n Centinela-VNet -o table`
  - `az network vnet subnet show -g NetworkWatcherRG --vnet-name Centinela-VNet -n Subnet-Storage -o json`
- Ver NSG y reglas:
  - `az network nsg show -g NetworkWatcherRG -n NSG-Centinela-Storage -o json`
  - `az network nsg rule list -g NetworkWatcherRG --nsg-name NSG-Centinela-Storage -o table`
- Ver Log Analytics (workspace):
  - `az monitor log-analytics workspace show -g NetworkWatcherRG -n Centinela-LogAnalytics -o table`
- Ver diagnostic settings del NSG:
  - `NSG_ID=$(az network nsg show -g NetworkWatcherRG -n NSG-Centinela-Storage --query id -o tsv)`
  - `az monitor diagnostic-settings list --resource $NSG_ID -o json`

Pruebas recomendadas (si queréis evidencia con tráfico real)
- Opción: desplegar dos VMs temporales en una región con capacidad (p. ej. `eastus`) y probar SSH/curl.
- Nota: el despliegue genera coste; eliminar VMs al terminar.

Rollback / eliminación de recursos (si fuera necesario)
- `az network nsg delete -g NetworkWatcherRG -n NSG-Centinela-Storage`
- `az network vnet delete -g NetworkWatcherRG -n Centinela-VNet`
- `az monitor log-analytics workspace delete -g NetworkWatcherRG -n Centinela-LogAnalytics`

Notas y recomendaciones
- La creación de nuevos NSG Flow Logs está bloqueada en algunas cuentas (retirada futura). Recomendamos migrar a *Virtual Network Flow Logs* según la guía de Azure.
- Mantener logs y retention adecuados (Log Analytics) y añadir alertas para eventos críticos.
- Considerar implementar Azure Policy para garantizar tags y naming estandarizados.

Cómo compartir esto con el equipo
1. Subir este archivo al repositorio (ya está en `docs/networking-week1.md`).
2. Crear un commit y push con un mensaje claro y abrir un PR para revisión:
   - `git add docs/networking-week1.md`
   - `git commit -m "docs: Networking Week1 - Centinela (VNet, NSG, logging)"`
   - `git push origin <tu-branch>`
   - Abrir un Pull Request en GitHub con objetivo `main`/`develop`.
3. Alternativa rápida: descargar el archivo y enviarlo por correo o chat (Teams/Slack).

Contacto / quien lo implementó
- Implementado por: equipo de infraestructura (acciones ejecutadas vía Azure CLI). Para dudas contactad a la persona responsable del repo.

— Fin —
