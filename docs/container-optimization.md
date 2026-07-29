# Reporte de optimización de imágenes de contenedor

**Sprint 6 · Fase 1 — CENTINELA**
Fecha de las medidas: 2026-07-29 · Docker 29.6.1 · base `python:3.12-slim` · plataforma destino `linux/amd64`

---

## 1. Resultado

Las dos cargas del sistema se empaquetaron como imágenes multi-stage independientes:

| Imagen | En disco (descomprimida) | Descarga (comprimida) | Paquetes |
|---|---:|---:|---:|
| Línea base ingenua | 1240 MiB | 438,5 MiB | 41 |
| **`centinela-api`** | **174 MiB** | **56,2 MiB** | 49 |
| **`centinela-worker`** | **158 MiB** | **52,6 MiB** | 28 |

| Reducción frente a la línea base | En disco | Descarga |
|---|---:|---:|
| API | **−86,0 %** | **−87,2 %** |
| Worker | **−87,3 %** | **−88,0 %** |

La *línea base* no es un espantapájaros retórico: es exactamente lo que sale de
contenedorizar este repositorio sin decisiones — imagen `python:3.12` completa,
una sola etapa, `requirements.txt` entero (con `pytest` dentro) y `COPY . .`.
Se construyó y se midió igual que las otras dos para que la comparación sea real.

> El worker tiene **más** código que la API en cuanto a lógica de dominio pero
> **menos** imagen: no sirve HTTP, así que no arrastra `fastapi`, `uvicorn`,
> `starlette`, `python-multipart`, Blob Storage ni Key Vault. Esa asimetría es la
> razón de mantener dos cierres de dependencias en vez de uno compartido.

---

## 2. Metodología (por qué estos números y no los de `docker images`)

Con el almacén de imágenes de containerd —el que trae Docker 29— `docker images`
y `docker image inspect --format '{{.Size}}'` devuelven el **tamaño comprimido**
de los blobs, no lo que ocupa el contenedor en marcha. Y `docker history` atribuye
`0 B` a las capas propias cuando la imagen es una lista de manifiestos. Tomar
cualquiera de los dos como "el tamaño de la imagen" habría dado un reporte falso.

Las dos cifras se miden por separado, cada una con el método que corresponde:

```bash
# En disco (lo que ocupa el filesystem del contenedor en el nodo)
docker run --rm --user 0 --entrypoint sh <imagen> -c 'du -sxm / | cut -f1'

# Descarga (suma de blobs comprimidos: lo que se transfiere en un arranque en frío)
docker image inspect <imagen> --format '{{.Size}}'
```

Ambas importan por motivos distintos: la comprimida gobierna el arranque en frío
con escalado a cero y el consumo de cuota del registro; la descomprimida gobierna
el disco del nodo y la presión de caché.

---

## 3. De dónde sale cada MiB

Contribuciones medidas de forma aislada, no estimadas:

| Medida | Efecto | Cómo se midió |
|---|---:|---|
| Base `python:3.12` → `python:3.12-slim` | **−1000 MiB** | 1124 MiB vs 124 MiB (`du -sxm /` en cada base) |
| Cierre por carga: worker sin stack HTTP | **−16 MiB** en el worker | venv de 56 MiB (API) vs 40 MiB (worker) |
| Cierre por carga vs `requirements.txt` único | **−39 MiB** (API) / **−55 MiB** (worker) | 95 MiB de `site-packages` en la línea base |
| Multi-stage: fuera pip/setuptools/wheel y cachés | incluido arriba | el runtime solo recibe `COPY --from=builder /opt/venv` |
| Borrado del `pip` de la imagen base | **−7 MiB** | 181 → 174 MiB en la API tras el cambio |
| Exportador OTLP **HTTP** en vez de gRPC | **~−40 MiB evitados** | `opentelemetry-exporter-otlp-proto-grpc` arrastra `grpcio` |
| `.dockerignore` | contexto de build **90 MiB → ~1 MiB** | `backend/` son 92 400 KiB, de los que `.venv` son 90 856 KiB |

### El hallazgo del `pip`

La auditoría de capas (§4) destapó que `pip` seguía dentro del runtime pese al
`pip uninstall` del builder: ese `uninstall` limpiaba el virtualenv, pero
`python:3.12-slim` trae **su propio** `pip` en `/usr/local/lib/python3.12/site-packages`.
Se borra ahora explícitamente en la etapa de runtime. Además del tamaño, quita de
en medio la herramienta más cómoda para que alguien con ejecución de código dentro
del contenedor se traiga más código.

### Orden de capas

Las dependencias se copian e instalan **antes** que el código, en capas separadas:

```dockerfile
COPY requirements-api.txt ./     # cambia rara vez
RUN python -m venv /opt/venv && ...
COPY --chown=10001:10001 app ./app   # cambia en cada commit
```

Medido sobre esta máquina:

| Escenario | Tiempo |
|---|---:|
| Reconstrucción tras cambiar solo código | **3 s** |
| Reconstrucción completa sin caché | 20 s |

Con el orden invertido, cada commit reinstalaría los 49 paquetes.

---

## 4. Verificación de ausencia de secretos

Regla dura del sprint: **cero credenciales en código, repo, pipeline o imágenes**.
Se verifica con `infra/verify-image-secrets.sh`, que inspecciona **todas las capas**
del tar exportado, no el filesystem final — un secreto añadido en una capa y
borrado en otra posterior sigue siendo recuperable con `docker save`.

Seis comprobaciones por imagen, ambas en verde:

| Comprobación | API | Worker |
|---|:--:|:--:|
| Ninguna capa contiene `.env`, claves privadas ni credenciales por nombre | ✓ | ✓ |
| Ninguna capa contiene cadenas de conexión, SAS ni claves privadas | ✓ | ✓ |
| Sin secretos en las variables de entorno de la imagen | ✓ | ✓ |
| Sin credenciales en el historial de construcción (`ARG`/`RUN`) | ✓ | ✓ |
| Arranca sin privilegios (`User=10001:10001`) | ✓ | ✓ |
| Sin gestor de paquetes dentro del contenedor | ✓ | ✓ |

### La auditoría se autoverifica

Una auditoría que siempre dice «todo bien» no prueba nada. Con `--self-test` se
construye una imagen trampa que copia un `.env` con una cadena de conexión y una
DSN de PostgreSQL, y **lo borra en una capa posterior**; la auditoría debe
rechazarla. Lo hace.

```
✓ la auditoría rechaza la imagen trampa (incluso con el .env borrado
  en una capa posterior, que es justo el caso peligroso)
```

### Dos falsos positivos, descartados con motivo

El primer pase marcó dos cosas que **no** son secretos, y conviene dejar por
escrito por qué se descartaron en lugar de silenciar la regla:

- `-----BEGIN PRIVATE KEY-----` en `cryptography/…/ssh.py` y `msal/application.py`:
  son las **cabeceras PEM** que esas librerías saben parsear, escritas en su código
  fuente. El patrón se afinó para exigir material base64 detrás de la cabecera.
- `GPG_KEY=7169605F62C751356D054A26A821E680E5FA6305`: lo define la imagen oficial
  de Python. Es la **huella pública** del firmante de CPython, publicada en
  python.org. Está en una lista de permitidos explícita y comentada.

### Dónde viven los secretos entonces

| Secreto | Dónde | Cómo llega al contenedor |
|---|---|---|
| `cosmos-db-key`, `cases-db-dsn`, `api-keys` | Key Vault | Secreto de Container Apps por `keyvaultref` + Managed Identity |
| Colas y Blob Storage | — | RBAC sobre la Managed Identity: no hay credencial |
| Publicación en GHCR | — | `GITHUB_TOKEN` efímero de Actions; no hay PAT en el repo |
| Pull desde GHCR | — | Paquete público: **pull anónimo, sin credencial** |

**El sistema no tiene ningún secreto de larga duración.** Con el paquete público
desaparece el token de *pull*, que era el único (§6). Si se vuelve a
`REGISTRY_VISIBILITY=private`, el script lo exige de nuevo y lo gestiona sin que
aparezca nunca en la línea de comandos: se siembra en Key Vault con
`az keyvault secret set --file` y Container Apps lo resuelve por referencia.

---

## 5. Free tiers y coste

| Servicio | Capa gratuita | Cómo se aprovecha |
|---|---|---|
| Azure Container Apps | 180 000 vCPU-s + 360 000 GiB-s + 2 M peticiones/mes | A 0,25 vCPU / 0,5 GiB son **~200 h/mes de una réplica**. Con `min-replicas=0` en ambas apps, sin tráfico el gasto es 0. |
| GHCR (paquetes **públicos**) | Almacenamiento y transferencia **ilimitados y gratuitos** | Las dos imágenes suman ~109 MiB por juego de etiquetas; las capas se comparten entre etiquetas. |
| Log Analytics / App Insights | 5 GB/mes de ingesta | Retención puesta a 7 días. |

**Estimación de crédito para la Fase 1: ~0 USD**, mientras el escalado a cero
absorba la carga de demo. El objetivo del sprint (<60 USD, techo 200) no se ve
comprometido por la contenedorización.

### Un riesgo que se eliminó en vez de gestionarse

El plan original era publicar en GHCR **privado**. Al calcular el consumo apareció
un problema: con `min-replicas=0`, cada arranque en frío en un nodo sin caché
re-descarga las imágenes (~109 MiB el juego completo), y el plan Free de GitHub
solo da **1 GB/mes** de transferencia para paquetes privados — del orden de
**9 arranques en frío al mes** lo agotan. Los *pulls* desde Actions no cuentan;
los de Azure sí.

Al comprobar que **el repositorio ya es público**, la salida fue evidente: publicar
también el paquete. Las imágenes no contienen nada que el repositorio no exponga ya
—mismo código, más dependencias de PyPI— y la auditoría de §4 certifica que no
llevan secretos. A cambio:

- transferencia y almacenamiento **ilimitados y gratuitos**, el riesgo desaparece;
- **se elimina el único secreto de larga duración del sistema** (el PAT de *pull*),
  lo que acerca el despliegue a la regla del sprint más que la opción privada.

Se aparta así del enunciado literal («registro privado»), y es una desviación
consciente: con el código fuente público, un paquete privado protegía un artefacto
derivado de material ya público, y su precio era un PAT permanente más una cuota
que la arquitectura de escalado a cero tiende a agotar.

Volver atrás es una variable: `REGISTRY_VISIBILITY=private` en
`infra/variables.sh` reactiva el modelo con token en Key Vault. Y migrar a ACR
Basic (~5 USD/mes, *pull* por Managed Identity) es cambiar `REGISTRY` y
`REGISTRY_NAMESPACE`, no reescribir el despliegue.

---

## 6. Decisiones y sus renuncias

**GHCR en vez de ACR.** Gratis, que es lo que pedía el requisito de free tier
(ACR no tiene capa gratuita). Publicado como paquete **público** por las razones
de §5: con el repositorio ya abierto, es lo que deja el sistema sin ningún secreto
persistente.

**Worker propio en vez de Azure Functions en contenedor.** La imagen base
`mcr.microsoft.com/azure-functions/python:4-python3.12` pesa más de 1 GB — habría
hecho inalcanzable el objetivo de imagen slim. El coste es reimplementar lo que el
host de Functions daba gratis: reintento, cola *poison* y apagado limpio. Está
cubierto por pruebas (`tests/unit/test_worker_loop.py`).

**`function_app.py` sigue vivo.** No se borró. Comparte composition root con el
worker (`app/presentation/worker/composition.py`), de modo que ambos despliegues
cablean exactamente las mismas dependencias, y el checkpoint
`pre-sprint6-funcional` sigue siendo un rollback real.

**Sondas exentas del rate limit.** Container Apps sondea `/health` cada pocos
segundos desde la misma IP. Con el límite por defecto (10 req/min) la probe habría
recibido 429 y la plataforma habría reiniciado en bucle un contenedor sano. Hay
una prueba de regresión para esto y otra que confirma que el resto de rutas sigue
limitado.

---

## 7. Observabilidad

Instrumentado **durante** la contenedorización, no después, como pedía el sprint:

- Trazas y métricas OTLP en API (auto-instrumentación de FastAPI) y worker (span
  por mensaje + contadores de procesados, fallidos y apartados a *poison*).
- Exportador **OTLP/HTTP**: el de gRPC arrastra `grpcio` (~40 MiB de binarios) sin
  aportar nada en este flujo.
- El agente OTel gestionado del entorno de Container Apps recibe en `localhost` y
  reenvía a Application Insights: **ninguna clave de instrumentación dentro de la
  imagen**.
- Degrada a no-op sin `OTEL_EXPORTER_OTLP_ENDPOINT` **y** si faltan los paquetes.
  Por eso las 114 pruebas y el despliegue anterior en App Service siguen
  funcionando sin tocar nada.

---

## 8. Reproducir estas medidas

```bash
# 1. Recompilar los cierres pinneados (resuelve dentro de linux/amd64)
bash infra/compile-requirements.sh

# 2. Construir
docker build --platform linux/amd64 -f backend/Dockerfile.api    -t centinela-api:dev    backend
docker build --platform linux/amd64 -f backend/Dockerfile.worker -t centinela-worker:dev backend

# 3. Auditar (incluye el autotest del propio detector)
bash infra/verify-image-secrets.sh --self-test centinela-api:dev centinela-worker:dev

# 4. Medir
docker run --rm --user 0 --entrypoint sh centinela-api:dev -c 'du -sxm / | cut -f1'
docker image inspect centinela-api:dev --format '{{.Size}}'
```

El pipeline (`.github/workflows/containers.yml`) ejecuta los pasos 2 y 3 en cada
push y **publica solo si la auditoría pasa**; el tamaño de cada imagen queda en el
resumen del job.

---

## 9. Estado y siguiente paso

Construido, medido, auditado y probado en local: **imágenes listas**.

Secuencia de despliegue:

```bash
# 1. El pipeline publica las imágenes al hacer push de la rama.
git push origin fix/sprint6-fase0

# 2. PASO MANUAL, una sola vez: GHCR crea los paquetes como PRIVADOS por
#    defecto. Hay que marcarlos públicos o el pull anónimo fallará.
#    GitHub → Packages → centinela-api  → Package settings → Change visibility
#                     └→ centinela-worker → ídem

# 3. Desplegar.
export SUFFIX=sp5x1
bash infra/containerapps.sh
```

Hasta que eso corra, el sistema en producción sigue siendo App Service +
Function App, intacto y funcionando. El despliegue en Container Apps **no lo
toca**: conviven hasta validar los contenedores.
