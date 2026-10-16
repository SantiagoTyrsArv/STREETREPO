# Street Repo

Sistema Ciudadano de Reporte y Priorización de Daños en la Infraestructura Vial de Pasto, Nariño.
Proyecto de grado · Ingeniería de Software · Universidad Cooperativa de Colombia, Campus Pasto.

> **Estado:** fase 1 (cimientos) del MVP. Aún no hay funcionalidad de negocio.

## Componentes

| Carpeta | Contenido | Tecnología |
|---|---|---|
| `backend/` | API REST (`/api/v1`) | FastAPI · SQLAlchemy 2 · Alembic |
| `admin-web/` | Panel administrativo (pendiente, fase 6) | React + Leaflet |
| `mobile/` | App ciudadana (pendiente, fase 7) | Flutter |
| `infra/` | Docker Compose, Dockerfiles, scripts de carga OSM | Docker · PostgreSQL + PostGIS |
| `docs/` | Decisiones de arquitectura (ADR) | — |

## Requisitos

- Docker Desktop (con Docker Compose v2)
- [uv](https://docs.astral.sh/uv/) para desarrollar el backend fuera de Docker

## Arranque rápido

```bash
cp .env.example .env                 # y cambiar POSTGRES_PASSWORD
docker compose -f infra/docker-compose.yml --env-file .env up --build
curl http://localhost:8000/health    # {"status":"ok"}
curl http://localhost:8000/ready     # comprueba PostgreSQL + PostGIS
# Documentación OpenAPI: http://localhost:8000/docs
```

El servicio `migrate` aplica las migraciones de Alembic antes de arrancar la API.

## Desarrollo del backend

```bash
cd backend
uv sync                              # instala dependencias (incluye las de desarrollo)
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest --cov                  # unitarias; las de integración se omiten sin base de datos
```

Pruebas de integración contra PostGIS (con la base de datos de Compose levantada):

```bash
docker compose -f infra/docker-compose.yml --env-file .env up -d db
cd backend
POSTGRES_HOST=localhost uv run alembic upgrade head
POSTGRES_HOST=localhost uv run pytest -m integration
```

Para activar los *hooks* de formato y lint antes de cada commit: `uvx pre-commit install`.

## Estructura del backend

```
backend/app/
├─ main.py            # create_app(): middlewares, errores, routers
├─ core/              # config, base de datos, errores uniformes, logs JSON, cabeceras, /health
├─ modules/           # auth, users, reports, confirmations, priority, roads, critical_services, admin
│  └─ <módulo>/       # presentation → application → domain ← infrastructure
└─ shared/
```

## Carga de datos OSM

Pendiente (fase 2).

## Decisiones

Ver [`docs/adr/`](docs/adr/README.md).
