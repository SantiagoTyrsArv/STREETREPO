# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versionado [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido
- Migración 0006: `usuario.version_politica`, `token_refresco` y `solicitud_supresion` (propuestas 8, 9 y 10).
- Autenticación: registro de ciudadanos con consentimiento de la versión vigente de la política,
  inicio de sesión con Argon2id, JWT de acceso de 15 min y refresco rotatorio con detección de
  reutilización, cierre de sesión, `GET /api/v1/me` y control de acceso por rol en el servidor.
- Comando `python -m app.cli create-admin` para crear administradores.

## [0.3.0] - 2026-10-16

Fase 3: dominio y priorización.

### Añadido
- Modelo de urgencia U = w1·S + w2·F + w3·P: pesos validados (rango 0–1, dos decimales,
  suma 1,00), normalización de S, F y P como estrategias intercambiables, marca "Revisar vía"
  y orden del ranking con desempate (severidad → confirmaciones → antigüedad).
- Máquina de estados del reporte (Registrado → Evaluado → Priorizado → Reparado): avances con
  salto permitidos (p. ej. Evaluado → Reparado) y sin retrocesos; solo el motor evalúa, el resto
  lo hace un administrador; cada cambio genera un registro de historial.
- Motor de priorización: evalúa un reporte con PostGIS local (vía a 30 m, servicio crítico a 500 m),
  guarda la evaluación reproducible, actualiza la U y la vía del reporte y lo pasa a Evaluado.
- Pesos versionados: cada cambio crea una versión vigente y recalcula los reportes activos en una
  sola transacción. Migración 0005 con la versión inicial 0,50 / 0,30 / 0,20.

### Seguridad
- Detección de secretos con `gitleaks` en pre-commit y en la CI (todo el historial; propuesta 21).

## [0.2.0] - 2026-10-15

Fase 2: datos geográficos.

### Añadido
- Migraciones 0003 y 0004: geometría `LineString` y etiqueta `highway_osm` en `via` (propuestas 6 y 7).
- Clasificación `highway` → jerarquía vial y factor de flujo F.
- Carga OSM idempotente (`python -m app.cli osm-import`) desde Overpass, con reintentos.
- Map-matching a la vía más cercana (≤ 30 m) y proximidad al servicio crítico más cercano (≤ 500 m)
  con PostGIS; radios como constantes con nombre en `shared/domain/geo_parameters.py`.

## [0.1.0] - 2026-10-15

Fase 1: cimientos.

### Añadido
- Estructura del monorepo: `backend/`, `admin-web/`, `mobile/`, `infra/`, `docs/`.
- API FastAPI con `/health` y `/ready`, formato de error uniforme, logs JSON con
  `X-Request-ID`, cabeceras de seguridad y CORS restringido al panel.
- Alembic con migración inicial que habilita PostGIS.
- Docker Compose (PostGIS 17-3.5, migraciones, API) e imagen de la API sin root.
- CI en GitHub Actions: ruff, mypy, pytest con PostGIS, pip-audit y build de Docker.
- Migración 0002 con las 10 entidades del diagrama ER, restricciones de integridad e índices
  GiST (`geometry` y `geography`); modelos ORM por módulo y mapeo en `docs/base-de-datos.md`.

[Sin publicar]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/SantiagoTyrsArv/STREETREPO/releases/tag/v0.1.0
