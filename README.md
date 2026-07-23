# CENTINELA

Proyecto organizado con Clean Architecture.

## Estructura

```
centinela/
├── backend/          # API (FastAPI) — domain / application / infrastructure / presentation
├── infra/            # Scripts de despliegue y variables
└── docs/             # Arquitectura, contrato API, ADRs y red
```

## Inicio rápido (backend)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## Documentación

- [Arquitectura](docs/architecture.md)
- [Contrato de API](docs/api_contract.md)
- [Decisiones](docs/decisions.md)
- [Red](docs/network.md)
- [Almacén de Casos (Especificación Técnica)](docs/cases_store_spec.md)
- [Justificación de Región (Entregable 3)](docs/region_justification.md)


