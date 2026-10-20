# Street Repo

Sistema Ciudadano de Reporte y Priorización de Daños en la Infraestructura Vial de Pasto, Nariño.
Proyecto de grado · Ingeniería de Software · Universidad Cooperativa de Colombia, Campus Pasto.

> **Estado:** fases 1 a 5 del MVP cerradas (versión `v0.5.0`): API base, esquema de base de datos,
> carga OSM, motor de priorización, autenticación, derechos del titular y reportes con foto y
> deduplicación a 25 m. Lo siguiente es la app Flutter y después el panel (decisión 44).
> Historial de versiones en [`CHANGELOG.md`](CHANGELOG.md).

## Componentes

| Carpeta | Contenido | Tecnología |
|---|---|---|
| `backend/` | API REST (`/api/v1`) | FastAPI · SQLAlchemy 2 · Alembic |
| `admin-web/` | Panel administrativo (pendiente, después de la app; decisión 44) | React + Leaflet |
| `mobile/` | App ciudadana (pendiente, la siguiente; decisión 44) | Flutter |
| `infra/` | Docker Compose, Dockerfiles, scripts de carga OSM | Docker · PostgreSQL + PostGIS |
| `docs/` | Decisiones de arquitectura (ADR) | — |

## Requisitos

- Docker Desktop (con Docker Compose v2)
- [uv](https://docs.astral.sh/uv/) 0.13.1 para desarrollar el backend fuera de Docker (la fija
  `required-version` en `backend/pyproject.toml`; actualizar con `uv self update 0.13.1`)

## Arranque rápido

```bash
cp .env.example .env                 # y cambiar POSTGRES_PASSWORD
docker compose -f infra/docker-compose.yml --env-file .env up --build
curl http://localhost:8000/health    # {"status":"ok","version":"<versión de la API>"}
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
infra/scripts/test-integration.sh          # acepta argumentos de pytest, p. ej. --cov o -k nearby
```

El script levanta la base de Compose, espera a que esté lista y corre `pytest` contra
`streetrepo_test` con las credenciales del `.env` de la raíz (la API solo lee `backend/.env`, así
que exportar `POSTGRES_HOST`, `POSTGRES_PORT` y `POSTGRES_DB` sin la contraseña no basta). En
Windows se ejecuta desde Git Bash.

Si el volumen de la base se creó antes de existir `infra/db/init/`, crear la base una vez:
`docker compose -f infra/docker-compose.yml --env-file .env exec db createdb -U streetrepo streetrepo_test`.

Para activar los *hooks* de formato, lint y detección de secretos (gitleaks) antes de cada commit:
`uvx pre-commit install`.

## Integración continua

La CI (`.github/workflows/ci.yml`) corre en cada *push* a cualquier rama: gitleaks, lint, tipos,
migraciones, pruebas con cobertura, auditoría de dependencias, imagen Docker y el análisis de
**SonarQube Cloud** (proyecto `SantiagoTyrsArv_STREETREPO`, configuración en
`sonar-project.properties`). El análisis recibe la cobertura de pytest (`coverage.xml`) y usa solo el
secreto `SONAR_TOKEN` de GitHub Actions; la puerta de calidad se evalúa sobre el código nuevo.

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

## Autenticación

- `POST /api/v1/auth/register` (ciudadano; exige aceptar la política vigente, `PRIVACY_POLICY_VERSION`),
  `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout` y `GET /api/v1/me`.
- `GET /api/v1/privacy-policy` (pública): versión vigente de la política y su dirección
  (`PRIVACY_POLICY_URL`, obligatoria y con https en producción; en dev y test puede quedar vacía y responde `null`).
- Derechos del titular (Ley 1581): `PATCH /api/v1/me` actualiza nombre y correo, y
  `POST /api/v1/me/data-deletion-requests` suprime los datos de inmediato por anonimización (conserva
  los reportes sin descripción ni fotos y revoca las sesiones). Las fotos que no se puedan borrar en
  ese momento las recoge `python -m app.cli purge-orphan-photos` (conviene programarlo a diario). Cambiar el correo o suprimir la cuenta exige la
  contraseña actual. Decisiones en [ADR 0006](docs/adr/0006-derechos-del-titular.md).
- Límite de intentos: bloqueo progresivo por correo tras 5 fallos seguidos (1 a 15 min) y límite por
  IP en inicio de sesión (30 cada 5 min) y registro (30 por hora, `REGISTER_PER_IP_PER_HOUR`); responde
  429 con `Retry-After`. Los cupos por IP son holgados porque los operadores móviles comparten una IP
  entre muchos usuarios (decisión 58); para una prueba con varias personas en la misma red, súbelos en `.env`.
  Contadores en memoria de un solo proceso ([ADR 0005](docs/adr/0005-limite-de-intentos.md)).
- Requiere `JWT_SECRET_KEY` (al menos 32 caracteres: `openssl rand -hex 32`) en `.env`.
- Administradores: `python -m app.cli create-admin --name "Nombre" --email correo@dominio.co`
  (pide la contraseña sin mostrarla). Decisiones en [ADR 0004](docs/adr/0004-autenticacion.md).

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

## Reportes

- `POST /api/v1/reports` (ciudadano con sesión): formulario `multipart/form-data` con `photo`,
  `longitude`, `latitude`, `severity` (`baja`, `media`, `alta`) y `description` opcional (hasta
  500 caracteres). Responde **201** con el reporte ya evaluado (U, dirección y «Revisar vía»).
- Posible duplicado (HU-15): `GET /api/v1/reports/nearby?longitude=…&latitude=…` lista los reportes
  activos a 25 m, sin autor y con la ubicación redondeada a 4 decimales (la distancia se mide desde
  ella). El punto debe estar dentro del área de servicio y cada usuario tiene un cupo de consultas por
  hora. `POST /api/v1/reports` responde **409** `REPORT_DUPLICATE_NEARBY` con esa lista, salvo que
  llegue `create_anyway=true`. Cada candidato lleva `is_mine` (propuesta 48).
- Confirmar (HU-16): `POST /api/v1/reports/{id}/confirmations` responde **201** con el total de
  confirmaciones; **409** si el reporte está reparado (`REPORT_NOT_ACTIVE`), es propio
  (`CONFIRMATION_OWN_REPORT`) o ya se confirmó (`CONFIRMATION_ALREADY_EXISTS`); **404** si no existe.
  No cambia U.
- Mis reportes: `GET /api/v1/me/reports?limit=&offset=` (máximo 50) lista los reportes creados
  (`relation: own`, completos) y los confirmados (`relation: confirmed`, vista pública sin autor,
  descripción ni ubicación exacta), del más reciente al más antiguo.
- Detalle: `GET /api/v1/reports/{id}` con el historial de estados; completo para el autor y los
  administradores (`relation: staff` si el administrador no es el autor), vista pública con
  observaciones ocultas para quien lo confirmó, y **404** para
  los demás.
- Cabecera opcional `Idempotency-Key` (UUID): un reintento con la misma clave responde **200** con
  el reporte que ya existe, sin duplicarlo ni consumir cupo. Si la clave llega con otra ubicación,
  severidad o descripción, responde **422** `IDEMPOTENCY_KEY_REUSED`.
- Una petición con `Content-Length` mayor que 10 MB más 64 KB de formulario se rechaza con **413**
  `PHOTO_TOO_LARGE` antes de recibir la foto; sin esa cabecera, el límite lo pone el proxy (HU-17).
- Foto: JPEG, PNG o WebP según su contenido, hasta 10 MB; se recodifica a JPEG sin metadatos (EXIF,
  GPS) con lado máximo de 1600 px y una miniatura de 400 px, en `PHOTO_STORAGE_DIR`.
- Solo se reciben reportes dentro de `REPORT_AREA_BBOX` (422 `LOCATION_OUTSIDE_SERVICE_AREA`) y hasta
  10 por hora por usuario y 100 por hora por IP (429 con `Retry-After`).

- `GET /api/v1/reports/{id}/photo` y `.../photo/thumbnail`: la foto y su miniatura, solo para el
  autor del reporte y los administradores (404 para los demás), sin caché.

Decisiones en [ADR 0007](docs/adr/0007-creacion-de-reportes.md).

## Base de datos

Esquema según el diagrama ER: ver [`docs/base-de-datos.md`](docs/base-de-datos.md).

## Respaldos

Los datos viven en dos volúmenes de Docker y se respaldan juntos, porque `evidencia.url_foto`
apunta a archivos del segundo:

```bash
# Base de datos
docker compose -f infra/docker-compose.yml exec db pg_dump -U streetrepo -Fc streetrepo > streetrepo.dump
# Fotos de evidencia (volumen street-repo_photos)
docker run --rm -v street-repo_photos:/fotos:ro -v "$PWD":/respaldo alpine \
  tar czf /respaldo/fotos.tar.gz -C /fotos .
```

## Decisiones

Bitácora de decisiones y propuestas: [`docs/bitacora.md`](docs/bitacora.md). Detalle técnico en
[`docs/adr/`](docs/adr/README.md) y ajustes pendientes del documento de la tesis en
[`docs/ajustes-tesis.md`](docs/ajustes-tesis.md).
