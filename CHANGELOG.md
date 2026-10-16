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
- Migración 0002 con las 10 entidades del diagrama ER, restricciones de integridad e índices
  GiST (`geometry` y `geography`); modelos ORM por módulo y mapeo en `docs/base-de-datos.md`.
- Migraciones 0003 y 0004: geometría `LineString` y etiqueta `highway_osm` en `via` (propuestas 6 y 7).
- Clasificación `highway` → jerarquía vial y factor de flujo F.
- Carga OSM idempotente (`python -m app.cli osm-import`) desde Overpass, con reintentos.
- Map-matching a la vía más cercana (≤ 30 m) y proximidad al servicio crítico más cercano (≤ 500 m)
  con PostGIS; radios como constantes con nombre en `shared/domain/geo_parameters.py`.
- Modelo de urgencia U = w1·S + w2·F + w3·P: pesos validados (rango 0–1, dos decimales,
  suma 1,00), normalización de S, F y P como estrategias intercambiables, marca "Revisar vía"
  y orden del ranking con desempate (severidad → confirmaciones → antigüedad).
