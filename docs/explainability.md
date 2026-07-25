# Explicador de casos (Semana 3) — contrato compartido

Base sobre la que trabajan mensajería, gestión de casos, seguridad y la API.
Responde, para cada decisión de scoring, **"¿por qué se abrió este caso?"** en
lenguaje que un analista entiende, a partir de la evidencia que ya produce el
motor (reglas activadas + valores observados).

## Piezas y responsables

| Pieza | Archivo | Estado | Dueño |
|-------|---------|--------|-------|
| Explicación (dominio) | [`explanation.py`](../backend/app/domain/entities/explanation.py) | ✅ contrato | Jorge |
| Catálogo legible de reglas | [`rule_catalog.py`](../backend/app/domain/value_objects/rule_catalog.py) | ✅ | Jorge |
| Puerto `Explainer` | [`explainer.py`](../backend/app/domain/services/explainer.py) | ✅ | Jorge |
| Explicador de referencia | [`rule_based_explainer.py`](../backend/app/application/services/rule_based_explainer.py) | ✅ base | Jorge |
| Serialización JSON (cola/persistencia) | [`explanation_dto.py`](../backend/app/application/dtos/explanation_dto.py) | ✅ contrato | Jorge |
| Puerto de lectura de casos | [`case_read_repository.py`](../backend/app/domain/repositories/case_read_repository.py) | ✅ contrato | Jorge |
| Schema HTTP de caso | [`case_schema.py`](../backend/app/presentation/schemas/case_schema.py) | ✅ contrato | Jorge |
| Endpoint `GET /cases/{caseId}` | [`cases.py`](../backend/app/presentation/api/routes/cases.py) | 🟡 stub 501 | Juanjose + Lucas |

## Contrato JSON de la explicación (camelCase)

Lo que viaja por la cola de casos y se persiste/expone:

```json
{
  "transactionId": "550e8400-e29b-41d4-a716-446655440000",
  "accountId": "acc-001",
  "score": 55,
  "threshold": 50,
  "isCase": true,
  "summary": "Caso abierto: score 55/50. 2 señales: Velocidad de transacciones inusual, Monto atípico.",
  "generatedAt": "2026-07-25T12:00:00Z",
  "reasons": [
    {
      "ruleId": "velocity",
      "title": "Velocidad de transacciones inusual",
      "description": "La cuenta realizó demasiadas transacciones en una ventana corta.",
      "detail": "6 transacciones en 10 min (límite 5).",
      "points": 25,
      "observed": { "count_in_window": 6, "window_minutes": 10, "limit": 5 }
    }
  ]
}
```

## Puntos de inserción para el equipo

- **Mensajería (Camila):** al abrir el caso, adjuntar `serialize_explanation(...)`
  al mensaje de la cola `cases`. El explicador se invoca con el `ScoringResult`.
- **Gestión de casos (Juanjose):** persistir la explicación (auditada/inmutable)
  e implementar `CaseReadRepository`; rellenar el endpoint `GET /cases/{caseId}`
  mapeando `CaseDetail` → `CaseDetailResponse`.
- **Seguridad (Lucas):** proteger `GET /cases/{caseId}` con `require_roles(...)`
  (lectura para Analista/Auditor/Administrador) y resolver el acceso temporal
  (SAS) a los documentos del caso.

**Regla:** no cambiar la forma de `Explanation` / `CaseDetailResponse` sin
acordarlo con mensajería y casos. Decisión en `decisions.md` (ADR-014).
