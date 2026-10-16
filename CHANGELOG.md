# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versionado [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido
- Estructura del monorepo: `backend/`, `admin-web/`, `mobile/`, `infra/`, `docs/`.
- API FastAPI con `/health` y `/ready`, formato de error uniforme, logs JSON con
  `X-Request-ID`, cabeceras de seguridad y CORS restringido al panel.
- Alembic con migración inicial que habilita PostGIS.
- Docker Compose (PostGIS 17-3.5, migraciones, API) e imagen de la API sin root.
- CI en GitHub Actions: ruff, mypy, pytest con PostGIS, pip-audit y build de Docker.
