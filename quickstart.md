# Quickstart — CENTINELA (Semana 1)

## Requisitos
- Python 3.12 (o 3.11+)

## Setup local (backend)
```bash
cd backend
python -m venv .venv
# Windows (PowerShell/CMD):
# .venv\Scripts\activate
# (Si usas PowerShell, alternativa: . .venv\Scripts\Activate.ps1)

pip install -r requirements.txt
```

## Ejecutar la API
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Probar Health
```bash
curl http://localhost:8000/health
```

## Probar Ingestión (Semana 1)
### Request
```bash
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transactionId": "b9a3d2f6-3e2b-4c5f-8e4b-3d3d7a0a9d55",
    "accountId": "string",
    "amount": 50000,
    "currency": "COP",
    "merchantId": "MERCHANT001",
    "merchantCategory": "SUPERMARKET",
    "timestamp": "2026-07-17T15:45:22Z",
    "location": {"latitude": 6.2442, "longitude": -75.5812}
  }'
```

### Expected
- `202 Accepted`
- Body ejemplo:
```json
{"transactionId":"<uuid>","accepted":true}
```

## Ejecutar Tests
```bash
pytest -q
```

