# Motor de scoring de fraude — CENTINELA (módulo Andrés)

## Objetivo

Función **serverless** que, ante el **evento de una transacción**, calcula un
score de fraude evaluando 4 reglas y abre un caso si supera el umbral. **No se
invoca desde la API**: su único disparador es el evento (cola `transactions`).

## Secuencia

```
evento de transacción (cola)
   → consultar historial de la cuenta      (TransactionHistoryRepository)
   → evaluar las 4 reglas                   (domain/services/rules.py)
   → sumar puntos → score                   (ScoringEngine)
   → persistir score + detalle              (ScoreRepository)
   → publicar caso si score ≥ umbral        (CaseQueue)
```

Entrypoint: [`backend/function_app.py`](../backend/function_app.py) (Azure
Functions v2, `queue_trigger` sobre `transactions`). Caso de uso:
[`ScoreTransactionUseCase`](../backend/app/application/use_cases/score_transaction.py).

## Las 4 reglas

Cada regla devuelve un `RuleResult` con `triggered`, `points` y **`observed`**:
los valores concretos que la activaron (no solo el id de la regla).

| Regla | id | Se activa cuando | Valores observados | Puntos |
|-------|----|------------------|--------------------|--------|
| Velocidad | `velocity` | ≥ N transacciones de la cuenta en una ventana de M min | `count_in_window`, `window_minutes`, `limit` | 25 |
| Monto atípico | `atypical_amount` | monto > factor × promedio de la cuenta (o > tope absoluto sin historial) | `amount`, `limit`, `basis`, `account_average`/`absolute_cap` | 30 |
| Geo-imposible | `geo_impossible` | velocidad implícita entre 2 transacciones > tope físico | `distance_km`, `minutes_since_last`, `implied_speed_kmh`, `max_speed_kmh`, `from`, `to` | 45 |
| Comercio de riesgo | `risky_merchant` | categoría del comercio en el conjunto de riesgo | `merchant_category`, `risky_categories` | 20 |

## Umbral y criterio (decisión de arquitectura)

**Umbral por defecto: 50** (ver [ADR-009](./decisions.md#adr-009-umbral-de-scoring-de-fraude-y-criterio-de-decisión)).

El compromiso es **falsos positivos vs. fraude no detectado**. Con estos pesos,
**ninguna regla sola abre un caso**; se exige corroboración:

| Escenario | Suma | ¿Caso? |
|-----------|------|--------|
| Solo comercio de riesgo (20) | 20 | No |
| Solo velocidad (25) | 25 | No |
| Solo geo-imposible (45) | 45 | No (ruido de geolocalización) |
| Monto atípico + comercio de riesgo (30+20) | 50 | Sí |
| Geo-imposible + comercio de riesgo (45+20) | 65 | Sí |
| Velocidad + monto atípico (25+30) | 55 | Sí |

Subir el umbral = más estricto (menos casos, menos falsos positivos); bajarlo =
más sensible. **Se cambia sin redeploy** (siguiente sección).

## Configuración sin redespliegue

Todo se lee de variables de entorno / **app settings** (no del código). Cambiar
un app setting reinicia la función y aplica el nuevo valor **sin redeploy**.

| App setting | Default | Efecto |
|-------------|---------|--------|
| `FRAUD_SCORE_THRESHOLD` | `50` | Umbral para abrir caso |
| `FRAUD_WEIGHT_VELOCITY` / `_ATYPICAL_AMOUNT` / `_GEO_IMPOSSIBLE` / `_RISKY_MERCHANT` | `25/30/45/20` | Puntos por regla |
| `FRAUD_VELOCITY_MAX_TX` / `FRAUD_VELOCITY_WINDOW_MIN` | `5` / `10` | Umbral de velocidad |
| `FRAUD_AMOUNT_FACTOR` / `FRAUD_AMOUNT_MIN_HISTORY` / `FRAUD_AMOUNT_ABSOLUTE_CAP` | `3.0` / `3` / `1000000` | Monto atípico |
| `FRAUD_GEO_MAX_SPEED_KMH` | `900` | Velocidad física máxima |
| `FRAUD_RISKY_CATEGORIES` | `gambling,crypto,wire_transfer,gift_cards,adult` | Categorías de riesgo |

Construcción de la config: `settings.scoring_config` en
[`settings.py`](../backend/app/infrastructure/config/settings.py).

## Contrato del evento

Mensaje en la cola `transactions` (JSON, camelCase). Lo parsea
[`transaction_from_event`](../backend/app/application/dtos/scoring_dto.py):

```json
{
  "transactionId": "550e8400-e29b-41d4-a716-446655440000",
  "accountId": "acc-001",
  "amount": "150000.50",
  "currency": "COP",
  "merchantId": "mer-9",
  "merchantCategory": "crypto",
  "timestamp": "2026-07-23T12:00:00Z",
  "latitude": "35.6762",
  "longitude": "139.6503"
}
```

## Persistencia del detalle

`ScoreRepository.save(ScoringResult)` guarda el score total, el umbral aplicado y
**el `observed` de cada regla activada** (los valores que la dispararon). En
producción es el mismo almacén NoSQL de la transacción (Cosmos, ver
[`nosql.md`](./nosql.md)).

## Integración pendiente (composition root)

Por defecto la función usa adaptadores **en memoria** (igual que el resto del
repo). Para producción se reemplaza en `build_use_case()` de `function_app.py`:

- Historial y persistencia de score → adaptador **Cosmos DB**.
- Cola de casos → **Azure Queue** que consuma el almacén relacional de casos.

El caso de uso y las reglas no cambian.

## Definition of Done — mapeo

| Criterio (DoD) | Evidencia |
|----------------|-----------|
| Pruebas que activan cada una de las 4 reglas | [`tests/unit/test_fraud_rules.py`](../backend/tests/unit/test_fraud_rules.py) |
| El umbral cambia sin redeploy y el comportamiento cambia | [`test_score_transaction.py`](../backend/tests/unit/test_score_transaction.py) `::test_threshold_change_without_redeploy_changes_behavior` |
| Cada regla activada persiste los valores concretos | `RuleResult.observed` + `test_scoring_engine.py::test_engine_persists_concrete_observed_values_per_rule` |
| Reacciona a un evento; NO invocado por la API | `queue_trigger` en `function_app.py` + `test_score_transaction.py::test_ingestion_is_decoupled_from_scoring` |

- **Entregable 5** — función serverless activada por el evento: `function_app.py`.
- **Entregable 6** — 4 reglas + suma + persistencia de score/detalle: `domain/services/` + `ScoreTransactionUseCase`.
- **Entregable 7** — publicación de caso al superar el umbral: `CaseQueue`.

Revisa el PR (debe aprobar): **Jorge**.
