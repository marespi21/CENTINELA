# CENTINELA — Backend

API del proyecto CENTINELA, organizada con Clean Architecture.

## Estructura

```
app/
├── domain/           # Entidades, value objects, repositorios (puertos) y excepciones
├── application/      # Casos de uso, DTOs e interfaces de aplicación
├── infrastructure/   # Azure, repositorios, persistencia, config y logging
└── presentation/     # API (routes, dependencies, middlewares) y schemas
```

## Requisitos

- Python 3.11+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Ejecutar

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

```bash
pytest
```
