# Justificación de Región de Despliegue — CENTINELA

**Autor:** Juan José Guarín  
**Proyecto:** CENTINELA  
**Entregable:** Entregable 3 (Justificación de región)

---

## 1. Selección de Regiones

- **Región Primaria (Infraestructura y Datos):** `eastus` (Este de EE. UU.)
- **Región de Cómputo (App Service Plan):** `centralus` (Centro de EE. UU.)

---

## 2. Criterios de Selección

### 2.1 Latencia y Proximidad Geográfica
- La región `eastus` ofrece una de las latencias más bajas hacia Latinoamérica (Colombia y región andina), garantizando tiempos de respuesta reducidos en las solicitudes de ingesta y gestión de casos.

### 2.2 Disponibilidad de Servicios en Nivel Gratuito (Free Tier)
- **Azure Database for PostgreSQL Flexible Server:** Disponibilidad garantizada de la SKU `Standard_B1ms` (Burstable) dentro del plan de prueba gratuita en `eastus`.
- **Azure Storage Account & Key Vault:** Disponibilidad completa de servicios de almacenamiento de objetos, colas y bóvedas de llaves en la misma región primaria.

### 2.3 Gestión de Cuotas de la Suscripción
- La cuota para **App Service Plan F1 (Free)** en la suscripción actual presentó restricciones en `eastus`. Se seleccionó la región emparejada `centralus` para alojar la WebApp en nivel gratuito sin costos adicionales ni superación de límites de cuota de cómputo.

### 2.4 Eficiencia de Costos
- `eastus` y `centralus` corresponden a las regiones con los costos base por hora/recurso más competitivos en Microsoft Azure, maximizando el rendimiento del saldo asignado para el proyecto de 21 días.

---

## 3. Matriz de Servicios y Disponibilidad Verificada

| Servicio | Región Seleccionada | Nivel de Servicio / SKU | Estado de Cuota Verificado |
|---|---|---|---|
| PostgreSQL Flexible Server | `eastus` | `Standard_B1ms` (Free Tier) | OK / Habilitado |
| Azure Virtual Network & NSG | `eastus` | Estándar (Sin costo adicionado) | OK / Habilitado |
| Azure Storage (Blob + Queue) | `eastus` | `Standard_LRS` | OK / Habilitado |
| Azure Key Vault | `eastus` | Standard | OK / Habilitado |
| App Service Plan | `centralus` | `F1` (Free Tier) | OK / Habilitado |

---

## 4. Conclusión

La combinación de `eastus` para la capa de datos/red y `centralus` para el cómputo satisface el 100% de los requerimientos funcionales, respeta las restricciones de presupuesto ($0 USD en Free Tier) y cumple rigurosamente con los criterios del Entregable 3 del proyecto CENTINELA.
