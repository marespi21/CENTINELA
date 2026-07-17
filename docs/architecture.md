# Arquitectura — CENTINELA

## Visión general

CENTINELA sigue **Clean Architecture** / **Arquitectura Hexagonal**, con dependencias que apuntan hacia el dominio.

## Capas

| Capa | Responsabilidad |
|------|-----------------|
| **domain** | Entidades, value objects, puertos de repositorio y excepciones de negocio |
| **application** | Casos de uso, DTOs e interfaces de aplicación |
| **infrastructure** | Implementaciones (Azure, persistencia, config, logging) |
| **presentation** | API HTTP (FastAPI), schemas, middlewares y manejo de errores |

## Flujo de dependencias

```
presentation → application → domain
       ↓            ↓
infrastructure ─────┘
```

La capa de dominio no depende de frameworks ni de infraestructura.

## Backend

Punto de entrada: `backend/app/main.py`.
