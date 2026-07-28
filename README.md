# CENTINELA

Proyecto organizado con Clean Architecture.

## Estructura

```
centinela/
├── backend/          # API (FastAPI) — domain / application / infrastructure / presentation
├── frontend/         # Consola Next.js del analista (bandeja de casos)
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

## Inicio rápido (consola)

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

La API key del analista (`ANALYST_API_KEY`) vive solo en el servidor Next (BFF).
Detalle en [`frontend/README.md`](frontend/README.md).

## Documentación

- [Arquitectura](docs/architecture.md)
- [Contrato de API](docs/api_contract.md)
- [Decisiones](docs/decisions.md)
- [Red](docs/network.md)
- [Almacén de Casos (Especificación Técnica)](docs/cases_store_spec.md)
- [Justificación de Región (Entregable 3)](docs/region_justification.md)
