# Mensajería — CENTINELA (módulo Camila, semana 2)

## Objetivo

Desacoplar la API del motor de scoring y garantizar la entrega de casos:

1. **Eventos de transacción** (req. 2.4): la API publica tras persistir y
   responde `202`; el scoring reacciona aparte.
2. **Cola de casos** (req. 2.5): scoring → gestión de casos con garantía de
   entrega (ningún caso se pierde si el consumidor está caído).

**Restricción:** está prohibido invocar el motor directamente desde la API.

## Flujo

```
POST /transactions
  → validar
  → persistir
  → publicar evento en cola `transactions`   ← módulo Camila
  → responder 202 Accepted                     (sin esperar scoring)

cola `transactions`
  → Azure Function (score_transaction)         ← módulo Andrés / Jorge
  → si score ≥ umbral → publicar en cola `cases`  ← puerto CaseQueue (Camila)
  → consumidor de gestión de casos                 ← Juan José
```

## Recursos

| Cola | Nombre default | Propósito |
|------|----------------|-----------|
| Eventos de transacción | `transactions` (`QUEUE_NAME` / `TRANSACTIONS_QUEUE`) | API → scoring |
| Casos | `cases` (`CASES_QUEUE`) | scoring → gestión de casos (durable) |

Aprovisionamiento: [`infra/deploy.sh`](../infra/deploy.sh) pasos 7 y 7.6.
Variables: [`infra/variables.sh`](../infra/variables.sh).

## Código

| Pieza | Ruta |
|-------|------|
| Puerto evento | `backend/app/domain/repositories/transaction_event_publisher.py` |
| Serialización evento | `backend/app/application/dtos/transaction_event.py` |
| Caso de uso (publica tras save) | `backend/app/application/use_cases/receive_transaction.py` |
| Memoria (dev + pause/resume) | `backend/app/infrastructure/messaging/in_memory_transaction_event_publisher.py` |
| Azure evento | `backend/app/infrastructure/azure/transaction_event_publisher.py` |
| Puerto casos | `backend/app/domain/repositories/case_queue.py` |
| Azure casos | `backend/app/infrastructure/azure/case_queue.py` |
| Composition root API | `backend/app/presentation/api/dependencies/transactions.py` |
| Composition root Function | `backend/function_app.py` (`build_case_queue`) |

## Por qué mensajería (no invocación directa)

Ver [ADR-010](./decisions.md#adr-010-mensajería-asíncrona-frente-a-invocación-directa-del-motor)
y [ADR-011](./decisions.md#adr-011-evento-de-notificación-vs-cola-con-garantía-de-entrega).

## Prueba de desacoplamiento (entregable 10)

```bash
cd backend && pytest tests/unit/test_messaging_decoupling.py -v
```

| Criterio | Test |
|----------|------|
| API responde antes de que termine el scoring (timestamps) | `test_api_responds_before_scoring_finishes_timestamps` |
| Con consumidor de casos detenido, la API sigue | `test_api_keeps_accepting_when_case_consumer_is_stopped` |
| Al reactivar, cero casos perdidos | `test_pending_cases_are_processed_without_loss_when_consumer_restarts` |

## Consumidor de casos (Semana 3)

El caso publicado en la cola `cases` incluye el **payload de la explicación**
(contrato `serialize_explanation`, camelCase). Un consumidor durable —función
`persist_case` en `function_app.py`— lo entrega a gestión de casos:

- Parsea el mensaje ([`case_message_dto`](../backend/app/application/dtos/case_message_dto.py))
  y ejecuta [`PersistOpenedCaseUseCase`](../backend/app/application/use_cases/persist_opened_case.py).
- Persiste el caso y su explicación vía `CaseWriteRepository` (PostgreSQL en
  producción, memoria en dev/test).
- **Garantía de entrega:** la cola `cases` es durable; si el consumidor está
  caído, el mensaje permanece hasta procesarse (cero pérdida). La explicación
  sobrevive el ciclo caído/reactivado.
- Loop punta a punta y garantía en
  [`test_persist_case.py`](../backend/tests/unit/test_persist_case.py).

## Entregables

| # | Qué |
|---|-----|
| 8 | Mecanismo de eventos conectado a la API |
| 9 | Pipeline E2E (coordinación con Jorge / scoring) |
| 10 | Prueba reproducible de desacoplamiento |
| 14 | Decisiones ADR-010 y ADR-011 |
