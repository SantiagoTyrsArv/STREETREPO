# Street Repo

Sistema Ciudadano de Reporte y Priorización de Daños en la Infraestructura Vial de Pasto, Nariño.
Proyecto de grado · Ingeniería de Software · Universidad Cooperativa de Colombia, Campus Pasto.

> **Estado:** fases 1 a 3 del MVP cerradas (versión `v0.3.0`): API base, esquema de base de datos,
> carga OSM y motor de priorización. Aún no hay rutas de negocio (autenticación y reportes: fases 4 y 5).
> Historial de versiones en [`CHANGELOG.md`](CHANGELOG.md).

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

Pruebas de integración contra PostGIS. Corren **solo** contra una base cuyo nombre termina en
`_test` (algunas borran tablas al probar las migraciones); Compose crea `streetrepo_test` junto a la
de desarrollo y las pruebas aplican las migraciones solas. Usar `127.0.0.1` y no `localhost`: en
Windows `localhost` intenta primero IPv6 y Docker solo publica en IPv4.

```bash
docker compose -f infra/docker-compose.yml --env-file .env up -d db
cd backend
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 POSTGRES_DB=streetrepo_test uv run pytest
```

Si el volumen de la base se creó antes de existir `infra/db/init/`, crear la base una vez:
`docker compose -f infra/docker-compose.yml --env-file .env exec db createdb -U streetrepo streetrepo_test`.

Para activar los *hooks* de formato, lint y detección de secretos (gitleaks) antes de cada commit:
`uvx pre-commit install`.

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

Descarga de Overpass las vías (`highway` según la propuesta 7) y los servicios críticos
(`amenity=hospital|school`) del área `OSM_BBOX` y los guarda en PostGIS. Es idempotente:
se puede repetir y actualiza por `osm_id` sin duplicar; si falla, no guarda nada.

```bash
docker compose -f infra/docker-compose.yml --env-file .env run --rm api python -m app.cli osm-import
# o desde backend/ (base de Compose en 127.0.0.1:5433):
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 uv run python -m app.cli osm-import --bbox 1.16,-77.33,1.25,-77.23
```

Usa la API pública de Overpass con `User-Agent` identificable y reintentos con espera creciente
ante 429/5xx (máximo 3 intentos). No se ejecuta por cada reporte: el cálculo de F y P es local.
Las vías o servicios eliminados de OSM no se borran de la base en una nueva carga.

## Motor de priorización

Calcula la urgencia U = w1·S + w2·F + w3·P (0–10) de cada reporte con datos locales de PostGIS:
vía más cercana a 30 m (sin vía: F = 2 y "Revisar vía") y servicio crítico más cercano a 500 m.
Cada cálculo se guarda en `evaluacion_prioridad` con los factores, la distancia y la versión de pesos.

- Pesos versionados: la migración 0005 carga la versión inicial 0,50 / 0,30 / 0,20; guardar pesos
  nuevos crea otra versión vigente y recalcula los reportes activos en una sola transacción.
- Estados: Registrado → Evaluado (lo hace el motor) → Priorizado → Reparado; se permiten avances
  con salto y no retrocesos, y todo cambio queda en `historial_estado`.

Código: `backend/app/modules/priority/` y `backend/app/modules/reports/domain/status_machine.py`.
Las rutas HTTP del panel (pesos, ranking, cambio de estado) llegan en la fase 6.

## Base de datos

Esquema según el diagrama ER: ver [`docs/base-de-datos.md`](docs/base-de-datos.md).

## Decisiones

Ver [`docs/adr/`](docs/adr/README.md).
