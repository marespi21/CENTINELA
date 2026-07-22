# TODO - Centinela (Semana 1)

## Step 1: Construcción contrato + seguridad (Pydantic)
- [x] Crear schemas de Transaction (validaciones: UUID, timestamp, amount, currency, lat/long)
- [x] Configurar rechazo de campos extra


## Step 2: Clean Architecture (domain/application)
- [x] Crear entidad Transaction
- [x] Crear puerto/repository interface en domain
- [x] Crear Use Case IngestTransactionUseCase
- [x] Crear DTO interno


## Step 3: Persistencia Semana 1 (infra)
- [x] Implementar TransactionRepository in-memory


## Step 4: Presentación API (FastAPI)
- [ ] Crear router transactions
- [ ] Crear dependencia/“container” para ensamblar use case + repository
- [ ] Registrar router en `backend/app/main.py` con prefijo `/api/v1`

## Step 5: Error handling (seguridad)
- [ ] Mapear errores de validación a formato `{ detail, code }`
- [ ] Asegurar que no se filtra stacktrace

## Step 6: Tests
- [x] Tests unitarios del schema
- [x] Tests de integración del use case con repository fake
- [x] Tests e2e del endpoint `POST /api/v1/transactions`


## Step 7: Documentación
- [x] Crear `quickstart.md` con comandos + curl + pytest


