# CENTINELA — Backend

API de ingesta de transacciones (Semana 1), con Clean Architecture.

## Flujo

```text
POST /transactions
  → Route (presentation)
  → ReceiveTransactionUseCase (application)
  → TransactionRepository (domain port)
  → InMemoryTransactionRepository (infrastructure, temporal)
  → 202 Accepted
```

Azure Storage/Queue se conectará después cambiando solo la dependencia
en `presentation/api/dependencies/transactions.py`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Ejecutar

```bash
uvicorn app.main:app --reload
```

- Swagger: http://localhost:8000/docs
- Health: `GET /`

## Probar ingesta

```bash
curl -X POST http://localhost:8000/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "transactionId": "550e8400-e29b-41d4-a716-446655440000",
    "accountId": "acc-001",
    "amount": "150000.50",
    "currency": "COP",
    "merchantId": "mer-9",
    "merchantCategory": "restaurants",
    "latitude": "4.7110",
    "longitude": "-74.0721"
  }'
```

## Tests

```bash
pytest
```
