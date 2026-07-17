# Contrato de API — CENTINELA

## Base

- Protocolo: HTTP/JSON
- Prefijo (propuesto): `/api/v1`

## Endpoints

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio |

**Respuesta 200**

```json
{
  "status": "ok"
}
```

## Errores

Formato propuesto:

```json
{
  "detail": "Mensaje de error",
  "code": "ERROR_CODE"
}
```

## Notas

Documentar aquí los endpoints a medida que se implementen.
