# Contrato de API — CENTINELA

## Base

- Protocolo: HTTP/JSON (y `multipart/form-data` para subida de archivos)
- Documentación interactiva: `GET /docs` (Swagger)

## Endpoints

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/` | Estado del servicio |

**Respuesta 200**

```json
{
  "status": "running",
  "service": "Centinela"
}
```

### Transacciones

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/transactions` | Recibe y valida una transacción |

**Cuerpo (JSON)**

```json
{
  "transactionId": "550e8400-e29b-41d4-a716-446655440000",
  "accountId": "acc-001",
  "amount": "150000.50",
  "currency": "COP",
  "merchantId": "mer-9",
  "merchantCategory": "restaurants",
  "latitude": "4.7110",
  "longitude": "-74.0721"
}
```

**Respuesta 202**

```json
{
  "transactionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted"
}
```

### Documentos (Blob + Queue)

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/documents` | Sube un documento a Blob Storage y publica un evento en la Queue |

**Cuerpo (`multipart/form-data`)**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `file` | archivo | PDF o imagen. Tipos permitidos: `application/pdf`, `image/png`, `image/jpeg`. Tamaño máximo: 5 MB (configurable). |

**Respuesta 202**

```json
{
  "documentId": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
  "blobName": "e3b0c442-98fc-1c14-9afb-4c8996fb9242.pdf",
  "status": "accepted"
}
```

Tras almacenar el archivo, se publica en la Queue un evento:

```json
{
  "event": "document.uploaded",
  "documentId": "e3b0c442-98fc-1c14-9afb-4c8996fb9242",
  "blobName": "e3b0c442-98fc-1c14-9afb-4c8996fb9242.pdf",
  "filename": "recibo.pdf",
  "contentType": "application/pdf",
  "sizeBytes": 18,
  "uploadedAt": "2026-07-22T12:00:00+00:00"
}
```

## Errores

Formato general:

```json
{
  "detail": "Mensaje de error",
  "code": "ERROR_CODE"
}
```

| Código HTTP | `code` | Cuándo |
|-------------|--------|--------|
| `409` | `DUPLICATE_TRANSACTION` | Transacción ya recibida |
| `422` | `INVALID_TRANSACTION` | Transacción no cumple reglas de negocio |
| `422` | `EMPTY_DOCUMENT` | Documento sin contenido |
| `413` | `DOCUMENT_TOO_LARGE` | Documento excede el tamaño máximo |
| `415` | `UNSUPPORTED_DOCUMENT_TYPE` | Tipo de archivo no permitido |
| `422` | (validación FastAPI) | Cuerpo/campos inválidos |

## Colección Postman

`docs/postman/CENTINELA.postman_collection.json` — variable `baseUrl` (por defecto `http://localhost:8000`).
