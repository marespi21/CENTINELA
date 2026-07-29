# Explicador asíncrono

**Sprint 6 · Fase 4 — CENTINELA**

---

## 1. La idea

Sacar la explicación **cara** del camino crítico de detección de fraude, sin que
ningún caso llegue jamás a la bandeja sin explicación.

```
cola `cases` → persist_case → PostgreSQL      ← el caso YA está abierto y visible
                    └─→ cola `explanations` → enrich_explanation
                             → añade una versión enriquecida
```

## 2. Dos explicadores, no uno

| | Explicador por reglas (semana 3) | Enriquecedor (esta fase) |
|---|---|---|
| Dónde corre | Camino crítico, dentro del scoring | Asíncrono, tras persistir el caso |
| Coste | Plantillas sobre el catálogo: microsegundos | Servicio externo: lento y falible |
| Puede fallar | No | Sí, y no pasa nada |
| Garantía | **Ningún caso sin explicación** | Mejor narrativa cuando se pueda |

El primero **no se ha tocado**. Es lo que garantiza el suelo mínimo.

### Por qué no se quitó la explicación del mensaje de caso

Era la opción obvia —publicar el caso "pelado" y explicarlo después— y es
justo la que rompe el sistema. Dos motivos concretos:

1. `opened_case_from_message` **lanza** `ValueError("case message without
   explanation")` si el mensaje no la trae. El consumidor existente reventaría.
2. `Explanation` está marcada en su propio módulo como **contrato compartido**
   del sprint: la publica mensajería, la persiste gestión de casos y la devuelve
   la API. No se cambia sin acordarlo con esos módulos.

Además, medido el coste real, el explicador por reglas son plantillas: no era
el cuello de botella. Sacarlo del camino crítico habría añadido complejidad y
un modo de fallo nuevo a cambio de ahorrar microsegundos.

## 3. Append-only, no sobreescritura

`caso_explicaciones` ya era una tabla **append-only y auditada**, y el
repositorio de lectura ya tomaba la más reciente:

```sql
SELECT explanation FROM caso_explicaciones
WHERE caso_id = %s ORDER BY creado_en DESC LIMIT 1
```

Así que el enriquecimiento **añade una versión** y pasa a mostrarse solo, con
cero cambios en el camino de lectura. La explicación por reglas queda como traza
de lo que se dijo primero — que es exactamente lo que se le pide a una tabla de
auditoría.

## 4. El caso nunca depende del enriquecimiento

La propiedad que sostiene el diseño, con test propio para cada punto:

| Situación | Qué pasa |
|---|---|
| La cola de enriquecimiento falla al publicar | **No se propaga.** El caso está guardado. Propagarlo haría que la cola reintentara el mensaje del caso y **duplicaría casos de fraude** — mucho peor que quedarse sin narrativa |
| No hay enriquecedor configurado | Adaptador nulo: el caso conserva su explicación por reglas |
| El servicio de enriquecimiento cae | Se propaga y el worker reintenta (el caso ya está a salvo) |
| El caso no existe | Se descarta sin reintentar: sería un bucle infinito |
| Consumidor previo a esta fase | La cola es un parámetro opcional; sin ella todo sigue funcionando |

## 5. Pendiente: el servicio

`build_explanation_enricher()` devuelve hoy `NullExplanationEnricher`. **La
tubería completa está construida, probada y desplegable sin decidir todavía qué
servicio redactará la narrativa**: cola, consumidor, contrato de mensaje,
persistencia append-only, escalado KEDA y métrica.

Enchufar un servicio es implementar `ExplanationEnricher.enrich()` y devolverlo
desde ese composition root. El puerto recibe un `EnrichmentContext` con la
explicación base y —si está disponible— la transacción original.

> Se hereda gratis la propagación de traza de la Fase 3: `AzureExplanationQueue`
> se construye sobre `AzureQueueService`, así que el enriquecimiento cuelga de la
> misma traza que la transacción que abrió el caso.

## 6. Métrica

`centinela.explicaciones.enriquecidas` — cuántas explicaciones se enriquecieron
fuera del camino crítico. Comparada con `centinela.casos.abiertos` dice qué
porcentaje de casos llegó a tener narrativa enriquecida.

## 7. Estado

Implementado y probado (10 tests nuevos; **157 en total**). Como el resto del
Sprint 6, **sin validar contra Azure**: el despliegue sigue pendiente de que los
paquetes de GHCR pasen a públicos.
