# Verificación documental (OCR)

**Sprint 6 · Fase 2 — CENTINELA**

---

## 1. Qué problema resuelve

Cuando el motor abre un caso de fraude, el analista necesita decidir si el cargo
es legítimo. La prueba habitual es el comprobante: el cliente adjunta el ticket o
la factura de la compra. Hasta ahora ese documento se subía, se guardaba… y ahí
moría.

Esta fase cierra el circuito: el comprobante se lee automáticamente y se
**contrasta contra la transacción que originó el caso**, dejando un veredicto
que el analista ve en la bandeja.

```
POST /documents (+caseId) → Blob → cola `documents` → worker
   → OCR (Document Intelligence F0) → contraste → veredicto en el caso
```

## 2. Tres huecos que existían

Auditando el módulo de documentos antes de construir aparecieron tres cosas
rotas que esta fase repara, y conviene dejarlas por escrito porque explican por
qué el alcance es el que es:

| Hueco | Estado anterior |
|---|---|
| La cola `documents` **no tenía consumidor** | `UploadDocumentUseCase` publicaba `document.uploaded` y el mensaje se acumulaba sin que nadie lo leyera |
| `POST /documents` **no aceptaba un caso** | No había forma de saber a qué caso pertenecía un documento |
| Nadie escribía en `caso_documentos` | La tabla existía y `GET /cases/{id}/documents` la leía, devolviendo siempre lista vacía |

## 3. El veredicto

| Veredicto | Significado |
|---|---|
| `coincide` | Todo lo contrastable respalda la transacción |
| `discrepa` | Algún campo la contradice — **la señal de fraude** |
| `insuficiente` | Se leyó el documento, pero nada superó el umbral de confianza |
| `ilegible` | El OCR no extrajo ningún dato utilizable |

### Qué decide y qué no

- **Importe y fecha deciden.** Son hechos comparables sin ambigüedad.
- **El comercio es informativo.** La transacción guarda `merchant_id` (`m1`), un
  identificador opaco, no un nombre comercial. Compararlo contra el nombre
  impreso en un ticket real daría discrepancias falsas constantemente, así que
  se muestra en el desglose pero **nunca dicta el veredicto por sí solo**.
- **La confianza del OCR filtra antes de juzgar.** Un campo leído por debajo de
  `VERIFY_MIN_FIELD_CONFIDENCE` se descarta: no cuenta a favor ni en contra.
  Acusar de fraude por una cifra mal reconocida es peor que no decir nada.

### Tolerancias

Se admite la **mayor** de dos tolerancias, porque ninguna sirve sola: la
relativa gobierna importes altos y la absoluta evita falsos positivos en los
bajos, donde un 2 % es ruido.

| Variable | Defecto | Por qué |
|---|---|---|
| `VERIFY_AMOUNT_TOLERANCE_RATIO` | `0.02` | Absorbe redondeos, propinas e IVA prorrateado |
| `VERIFY_AMOUNT_TOLERANCE_ABSOLUTE` | `1000` | Protege importes pequeños |
| `VERIFY_DATE_WINDOW_DAYS` | `3` | El comercio puede liquidar con retraso |
| `VERIFY_MIN_FIELD_CONFIDENCE` | `0.60` | Umbral por debajo del cual no se juzga |

Son variables de entorno: afinarlas no exige reconstruir la imagen.

## 4. Reintentar o no: la decisión que importa

El worker solo borra un mensaje de la cola si el handler no lanza. Por eso la
distinción entre "resultado" y "fallo" es lo que evita bucles infinitos y
quemar la cuota gratuita:

| Situación | Tratamiento | Motivo |
|---|---|---|
| Documento ilegible | Veredicto `ilegible` persistido, mensaje borrado | Reintentar daría exactamente lo mismo y gastaría páginas F0 |
| OCR caído o sin cuota | Excepción → mensaje **reintentado** | Es un fallo transitorio del servicio |
| Caso o transacción inexistentes | Documento vinculado sin veredicto | El vínculo importa aunque no se pueda contrastar |
| Documento sin `caseId` | Se ignora, **sin llamar al OCR** | No hay nada contra qué contrastar; no se gasta cuota |
| Mensaje reprocesado | `ON CONFLICT DO UPDATE` | La cola entrega "al menos una vez" |

## 5. Coste — capa gratuita F0

| Recurso | Capa gratuita | Nota |
|---|---|---|
| Azure AI Document Intelligence | **F0**: 500 páginas/mes | Azure permite **una sola instancia F0 por suscripción** |

El worker procesa los documentos secuencialmente desde la cola, lo que encaja
con la concurrencia limitada de F0 sin necesidad de estrangular nada.

**Sin claves:** el worker se autentica con su Managed Identity y el rol
*Cognitive Services User* (permite invocar el análisis, no administrar el
recurso ni leer sus claves). Para que el servicio acepte tokens de Entra ID se
crea con subdominio personalizado. La Fase 2 **no añade ningún secreto** al
sistema.

## 6. Degradación sin OCR configurado

Sin `DOC_INTELLIGENCE_ENDPOINT` entra `NullDocumentAnalyzer`: el documento se
vincula al caso y queda con veredicto `ilegible`, pero el worker no falla ni
bloquea la cola. Es el mismo criterio que el resto del sistema aplica con Cosmos
y PostgreSQL — sin configuración, adaptador degradado, nunca un arranque
fallido. Gracias a eso los 22 tests nuevos corren sin tocar Azure.

## 7. Desplegar

```bash
export SUFFIX=sp5x1

# 1. Aprovisionar el OCR en capa gratuita (idempotente)
bash infra/document-intelligence.sh

# 2. Aplicar el DDL: añade las columnas de veredicto a caso_documentos.
#    Usa ALTER ... IF NOT EXISTS, así que es seguro sobre la base ya desplegada.
psql "$CASES_DB_DSN" -f scripts/init-cases-db.sql

# 3. Redesplegar el worker con el endpoint del OCR
bash infra/containerapps.sh
```

### Probar

```bash
API=https://<fqdn-de-la-container-app>
curl -X POST "$API/documents" \
  -H "X-API-Key: adm-key" \
  -F "file=@comprobante.pdf" \
  -F "caseId=<uuid-del-caso>"

# tras unos segundos, el veredicto aparece en el documento del caso
curl "$API/cases/<uuid-del-caso>/documents" -H "X-API-Key: adm-key"
```

## 8. Estado

Implementado y probado con dobles en memoria (22 tests nuevos; 139 en total).
**No validado todavía contra el servicio real de Document Intelligence** — eso
requiere el despliegue en Container Apps, pendiente de que los paquetes de GHCR
pasen a públicos. El parseo de campos del SDK es deliberadamente tolerante
(acepta atributos y claves de diccionario) porque la forma de los valores cambia
entre versiones, pero esa tolerancia es una precaución, no un sustituto de la
prueba contra el servicio.
