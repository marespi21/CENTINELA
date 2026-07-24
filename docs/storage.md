# Storage — CENTINELA (módulo Samuel)

## Objetivo

Almacenar documentos (comprobantes) en Azure Blob Storage de forma privada,
con nombres únicos y retención automática.

## Recursos

| Recurso | Nombre (default) | Notas |
|---------|------------------|-------|
| Storage Account | `st<proyecto><env>` (ej. `stcentineladev`) | StorageV2, `Standard_LRS`, sin acceso público a blobs. Único global. |
| Container | `documents` | Privado (`--public-access off`). |
| Queue documentos | `documents` | Evento `document.uploaded`. |
| Queue transacciones | `transactions` | Evento `transaction.received` (API → scoring). Módulo Camila. |
| Queue casos | `cases` | Caso abierto (scoring → gestión). Módulo Camila; entrega durable. |

Aprovisionamiento: [`infra/deploy.sh`](../infra/deploy.sh) (pasos 5–7.5).
Variables: [`infra/variables.sh`](../infra/variables.sh).

## Naming de blobs

Cada documento se guarda con un **UUID** + la extensión original
(ej. `3138a4d1-...-9265a1.pdf`), generado en `upload_document.py`.

## Servicio (código)

El "StorageService" es el puerto `BlobStorage` + su adaptador Azure:

- Puerto: [`app/domain/repositories/blob_storage.py`](../backend/app/domain/repositories/blob_storage.py) — `upload()`, `download()`, `exists()`.
- Azure: [`app/infrastructure/azure/blob_storage.py`](../backend/app/infrastructure/azure/blob_storage.py).
- En memoria (dev/test): [`app/infrastructure/repositories/in_memory_blob_storage.py`](../backend/app/infrastructure/repositories/in_memory_blob_storage.py).

Autenticación en Azure: **Managed Identity** (`DefaultAzureCredential`), con el
rol `Storage Blob/Queue Data Contributor` que asigna [`infra/security.sh`](../infra/security.sh).
La app deriva los endpoints de blob y queue del nombre `STORAGE_ACCOUNT`.

## Lifecycle

[`infra/lifecycle-policy.json`](../infra/lifecycle-policy.json), aplicada en `deploy.sh` (paso 6.5):

| Antigüedad | Acción |
|------------|--------|
| > 30 días | mover a **Cool** |
| > 90 días | mover a **Archive** |
| > 365 días | **eliminar** |

## Acceso privado

[`infra/private-network.sh`](../infra/private-network.sh) crea el **Private
Endpoint** del blob en la subnet de datos (Juanjo) y pone el storage en
`default-action Deny`. Requiere la VNet de `scripts/deploy-network.sh` y App
Service SKU B1+.
