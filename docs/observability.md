# Observabilidad

**Sprint 6 · Fase 3 — CENTINELA**

---

## 1. El problema que resuelve

Tras la Fase 1 el sistema ya emitía trazas, pero rotas. La API abría una traza al
recibir `POST /transactions` y el worker abría **otra** al procesar el mensaje:
dos trazas inconexas separadas por una cola.

Eso deja sin respuesta la pregunta que de verdad se hace en producción: *«este
caso tardó cuatro minutos en aparecer en la bandeja — ¿dónde se fue el tiempo?»*.
Con trazas partidas solo se puede ver que la API respondió rápido y que el worker
procesó rápido, sin poder afirmar nada del hueco entre ambos.

## 2. Trazado distribuido a través de las colas

Azure Queue Storage no tiene cabeceras de mensaje: el cuerpo es una cadena. Así
que el contexto W3C (`traceparent` / `tracestate`) viaja **dentro del JSON**, como
dos claves más.

```
POST /transactions          [trace abc123]
  └─ queue.publish transactions        ← inyecta traceparent en el mensaje
       └─ queue.process transactions   ← lo extrae: MISMO trace abc123
            └─ queue.publish cases     ← lo vuelve a inyectar
                 └─ queue.process cases
                      └─ INSERT en PostgreSQL
```

### Un solo punto de inyección

Todo envío a cola del sistema —transacciones, casos y documentos— construye su
adaptador sobre `AzureQueueService`. Por eso la inyección vive ahí y no en cada
productor: una línea cubre las tres colas y **no hay forma de olvidarse de una**
al añadir la cuarta.

La inyección ocurre *dentro* del span de publicación, no antes; si fuera al revés
el `traceparent` apuntaría al span equivocado y la cadena quedaría torcida.

### Compatible hacia atrás

Todos los parsers del sistema leen las claves que les interesan e ignoran el
resto, así que un mensaje con contexto lo entiende igual un consumidor antiguo, y
un mensaje sin contexto (publicado antes de esta fase) se procesa con normalidad
abriendo una traza nueva. Hay tests que fijan justo eso: si un mensaje con traza
tumbara al worker, sería mucho peor que no tener trazas.

## 3. Métricas

Las de la Fase 1 decían si el worker estaba **sano**. Estas dicen si el sistema
está **haciendo su trabajo**:

| Métrica | Tipo | Para qué |
|---|---|---|
| `centinela.transacciones.evaluadas` | contador | Volumen procesado, etiquetado por si abrió caso |
| `centinela.casos.abiertos` | contador | Cuántos fraudes se están detectando |
| `centinela.scoring.duracion` | histograma | Latencia del motor (percentiles, no media) |
| `centinela.reglas.activadas` | contador | **Qué** regla dispara los casos: dice si el motor está calibrado o si una regla se volvió ruidosa |
| `centinela.documentos.verificados` | contador | Veredictos OCR, etiquetado por resultado |
| `centinela.caso.latencia_extremo_a_extremo` | histograma | Desde que se puntuó la transacción hasta que el caso quedó guardado |

Histogramas y no contadores con media para las latencias: la media esconde justo
lo que interesa mirar, que es la cola de percentiles.

La latencia extremo a extremo se calcula con el `scoredAt` que **ya viajaba** en
el mensaje del caso, así que no hubo que almacenar ni propagar nada nuevo.

## 4. Logs correlacionados

Cada línea de log lleva `trace_id` y `span_id`, en el mismo formato hexadecimal
que usa Application Insights — se pueden pegar tal cual en el portal.

```
2026-07-29 11:40:19 INFO [trace=4bf92f3577b34da6a3ce929d0e0e4736 span=00f067aa0ba902b7] app...
```

Con `LOG_FORMAT=json` la salida es JSON estructurado, que es lo que conviene en
Container Apps: Log Analytics lo consulta por campos en vez de con `contains`.
En local se mantiene texto plano, que se lee mejor.

## 5. Alertas

Cada alerta responde a un fallo **real** de este sistema, no a una métrica
genérica de manual:

| Alerta | Qué significa si salta |
|---|---|
| `alerta-mensajes-envenenados` | Hay transacciones o casos que el sistema no consiguió procesar tras varios intentos: pérdida funcional silenciosa |
| `alerta-worker-con-errores` | El worker acumula fallos de cola; los casos de fraude dejan de llegar a la bandeja |
| `alerta-ocr-fallando` | Document Intelligence rechaza documentos — muy probablemente la cuota gratuita F0 agotada |

Consultas guardadas para investigar: traza completa por `trace_id`, casos por
ventana de tiempo, reparto de veredictos documentales y ranking de reglas más
activadas.

## 5b. Métricas: el agente de Container Apps no las acepta

Descubierto desplegando, no leyendo documentación. El agente OTel gestionado del
entorno reenvía **trazas y logs** a Application Insights, pero **no métricas**:
al exportarlas contra él responde con `Connection reset by peer`, y el SDK entra
en un bucle de reintentos que quema CPU y ahoga los logs de la aplicación con
avisos.

```
opentelemetry.exporter.otlp.proto.http.metric_exporter
  Transient error ('Connection aborted.', ConnectionResetError(104, ...))
  Failed to export metrics batch due to timeout, max retries or shutdown.
```

La solución respeta la convención estándar: `setup_telemetry` honra
`OTEL_METRICS_EXPORTER`, y el despliegue pone `OTEL_METRICS_EXPORTER=none` en
ambos contenedores. Las trazas siguen activas; los contadores e histogramas se
instancian igual pero no se exportan.

Para recuperarlos hay que darles un destino que sí los acepte: un colector OTLP
propio, o Datadog, ambos soportados por el agente. Mientras tanto, la
observabilidad operativa se apoya en trazas y en los logs estructurados, que sí
llegan.

> **Cuidado con `appInsightsConfiguration.connectionString`.** Al leerlo, Azure
> devuelve siempre `null` aunque esté configurado. No sirve para verificar nada:
> la única señal fiable de que el agente está bien conectado es que dejen de
> aparecer errores del exportador en los logs del contenedor.

## 6. Coste

Cero cómputo nuevo. La ingesta va contra los **5 GB/mes gratuitos** de Log
Analytics, con retención a 30 días —la SKU `PerGB2018` no admite menos, y los
primeros 31 días de retención no se cobran—. El agente OTel gestionado del entorno de
Container Apps recibe en `localhost` y reenvía a Application Insights, así que
**la aplicación no lleva ninguna clave de instrumentación dentro de la imagen**.

## 7. Nota sobre el entorno de pruebas

OpenTelemetry se añadió a `backend/requirements.txt`, no solo a las imágenes.
Sin eso los tests de propagación se **saltaban** en vez de ejecutarse —tanto en
local como en CI— y un test que siempre se salta no prueba nada. Ahora los 8
tests de propagación corren de verdad, incluido el que verifica que productor y
consumidor comparten `trace_id`.

## 8. Desplegar

```bash
export SUFFIX=sp5x1
export ALERT_EMAIL=tu@correo
bash infra/observability.sh
```

Requiere que `infra/containerapps.sh` haya creado antes el workspace de Log
Analytics y el Application Insights.

## 9. Estado

Implementado y probado (147 tests). **No validado contra Azure todavía**: las
trazas de punta a punta solo pueden comprobarse de verdad con los contenedores
desplegados y el agente OTel activo, y el despliegue sigue pendiente de que los
paquetes de GHCR pasen a públicos.
