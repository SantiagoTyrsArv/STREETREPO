# Objetivo 4: comparación con el panel de referencia — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir dentro del sistema la herramienta de la prueba piloto (HU-09): zonas, rondas congeladas, vista a ciegas para evaluadores, métricas de acuerdo, ficha comparativa y registro de avisos de duplicado.

**Architecture:** Un módulo nuevo `backend/app/modules/validation/` (capas domain / application / infrastructure / presentation) con las métricas como funciones puras sobre `scipy`. Cambios acotados en `auth` (rol evaluador y sesión web), `reports` (zona al crear, avisos de duplicado) y `confirmations` (enlace del aviso). En el panel, tres vistas de administrador y dos de evaluador; en la app, el envío del `duplicate_warning_id`.

**Tech Stack:** FastAPI, SQLAlchemy 2 + GeoAlchemy2, PostGIS, Alembic, `scipy` (nuevo), pytest; React + TypeScript + TanStack Query + react-leaflet, `@dnd-kit/sortable` (nuevo), Vitest + MSW, Playwright; Flutter + Riverpod.

**Spec:** `docs/superpowers/specs/2026-11-22-objetivo-4-comparacion-panel-referencia-design.md` (léelo completo antes de empezar; manda sobre este plan).

**Entregas:** Entrega 1 = tareas 1 a 9 (backend y CLI), rama `feat/validation-backend`. Entrega 2 = tareas 10 a 15 (panel y app), rama `feat/validation-panel`, creada desde `main` después de integrar la entrega 1. Cada tarea es un commit (o varios) en su rama; integrar con `git merge --no-ff` sin PR (guía 8.4).

## Global Constraints

- Guía `AGENTS.md` completa: capas con dependencias hacia el dominio, `mypy --strict` en dominio y aplicación, `ruff`, consultas parametrizadas, formato de error `{code, message, details}`, RBAC en el servidor, mensajes en español de Colombia, identificadores en inglés, tablas y columnas en español según el ER.
- Pruebas con cada tarea (TDD); cobertura ≥ 80 % en dominio y aplicación; las de integración corren con `infra/scripts/test-integration.sh`.
- Constantes con nombre en `backend/app/modules/validation/domain/parameters.py`: `MIN_REPORTS_PER_ZONE = 5`, `MAX_ZONES = 3`, `SIGNIFICANCE_ALPHA = 0.05`. Los servicios del minimapa usan `PROXIMITY_MAX_RADIUS_M` (500 m) de `app/shared/domain/geo_parameters.py`, sin duplicarlo.
- `scipy` fijado con versión exacta en `backend/pyproject.toml` y `uv.lock`; `@dnd-kit/core` y `@dnd-kit/sortable` fijados en `admin-web/package.json`. Registrar ambas como decisión menor en la bitácora.
- El evaluador nunca recibe de la API: `puntaje_u`, S, F, P, jerarquía vial, distancia al servicio, confirmaciones, estado, fecha, autor, `orden_motor` ni órdenes de otros evaluadores.
- Exportaciones CSV: separador coma, decimales con punto, UTF-8 con BOM (para Excel), evaluadores como «Evaluador 1…k» ordenados por su primer envío.
- Nada de esto genera resultados de la tesis; los datos de prueba son fixtures.

## Review Focus

1. **Fuga a ciegas por rutas laterales:** un evaluador que pide `/admin/...`, la foto de un reporte fuera de la ronda, o una zona ajena debe recibir 403/404 sin datos. → Pruebas en Tarea 6.
2. **Orden enviado inválido:** ids repetidos, faltantes, de otra zona o de otra ronda, lista vacía → 422 `EVALUATION_ORDER_INVALID` sin guardar nada. → Tarea 6.
3. **Dos administradores abren ronda a la vez:** el índice único parcial dispara `IntegrityError`; debe salir 409 `EVALUATION_ROUND_ALREADY_OPEN`, no 500. → Tarea 5.
4. **Empate total en el orden del motor** (misma U, severidad, confirmaciones y fecha): `orden_motor` debe ser 1..n estricto y reproducible; desempate final por `id_reporte`. → Tarea 5.
5. **GeoJSON defectuoso** (MultiPolygon, geometría inválida, polígonos que se solapan, falta `name` o `concentration`, nombre repetido): error claro y no se importa nada. → Tarea 3.

---

## Entrega 1 — backend y CLI (rama `feat/validation-backend`)

### Task 1: Migración 0009, modelos y rol evaluador

**Files:**
- Create: `backend/migrations/versions/20261123_0009_validacion_panel_referencia.py`
- Create: `backend/app/modules/validation/__init__.py` y subpaquetes `domain/`, `application/`, `infrastructure/`, `presentation/` (con `__init__.py`)
- Create: `backend/app/modules/validation/infrastructure/models.py`
- Modify: `backend/app/modules/users/domain/role.py` (añadir `EVALUATOR = "evaluador"`)
- Modify: `backend/app/modules/roads/infrastructure/models.py` (`ZoneModel`: `concentration`, `name` único)
- Modify: `backend/app/models.py` (registrar los modelos nuevos)
- Test: `backend/tests/integration/test_schema.py`, `backend/tests/unit/test_app_models_registry.py`

**Interfaces:**
- Produces (tablas, sección 9 del diseño): `zona.concentracion` ENUM `concentracion_zona(alta, baja)` NOT NULL, `uq_zona_nombre`; `ronda_evaluacion(id_ronda UUID PK, nombre VARCHAR(100), estado ENUM estado_ronda(abierta, cerrada), tamano_muestra SMALLINT CHECK > 0, semilla BIGINT, id_config FK configuracion_pesos, id_usuario FK usuario, fecha_apertura, fecha_cierre NULL)` con índice único parcial `uq_ronda_abierta ON (estado) WHERE estado = 'abierta'`; `ronda_reporte(id_ronda FK CASCADE, id_reporte FK RESTRICT, id_zona FK, puntaje_u NUMERIC(4,2), orden_motor SMALLINT)` con PK (id_ronda, id_reporte) y único (id_ronda, id_zona, orden_motor); `orden_evaluador(id_ronda, id_usuario FK, id_reporte, posicion SMALLINT, fecha_envio)` con FK compuesta (id_ronda, id_reporte) → `ronda_reporte` CASCADE, únicos (id_ronda, id_usuario, id_reporte); `aviso_duplicado(id_aviso UUID PK, id_usuario FK, id_zona FK NULL, fecha, decision ENUM decision_aviso(pendiente, confirmo, creo_igual) DEFAULT pendiente, id_reporte_resultante FK NULL SET NULL)`; `aviso_duplicado_candidato(id_aviso FK CASCADE, id_reporte FK CASCADE, distancia_m NUMERIC(6,2))` PK (id_aviso, id_reporte). `rol_usuario` gana `evaluador` (`ALTER TYPE … ADD VALUE`, fuera de transacción con `op.get_context().autocommit_block()`).
- Produces (ORM): `EvaluationRoundModel`, `RoundReportModel`, `EvaluatorOrderModel`, `DuplicateWarningModel`, `DuplicateWarningCandidateModel` en `validation/infrastructure/models.py`; `UserRole.EVALUATOR`.
- Note: la unicidad (ronda, usuario, zona, posición) no cabe en una restricción porque la zona vive en `ronda_reporte`; la garantiza la aplicación (Tarea 6).

- [ ] **Step 1:** En `test_schema.py`, añadir las cinco tablas y sus columnas al diccionario de columnas esperadas, `concentracion` a `zona`, y pruebas: `test_only_one_open_round` (dos INSERT con `estado='abierta'` → `IntegrityError` con `uq_ronda_abierta`), `test_round_report_order_is_unique_per_zone`, `test_report_in_round_cannot_be_deleted` (DELETE del reporte → `IntegrityError`), `test_evaluator_role_exists` (UPDATE de un usuario a `'evaluador'` funciona). Ejecutar el downgrade/upgrade existente de las pruebas de migración con 0009.
- [ ] **Step 2:** Correr `infra/scripts/test-integration.sh -k schema` → FALLA.
- [ ] **Step 3:** Escribir la migración (con `downgrade` que borra todo lo nuevo; el valor de ENUM `evaluador` no se puede quitar en PostgreSQL: el downgrade lo deja y lo documenta en el docstring), los modelos ORM y el registro.
- [ ] **Step 4:** `infra/scripts/test-integration.sh` completo → PASA; `uv run mypy` y `uv run ruff check .` limpios.
- [ ] **Step 5:** Commit `feat(validation): esquema de zonas, rondas y avisos de duplicado`.

### Task 2: Métricas de acuerdo (dominio puro)

**Files:**
- Modify: `backend/pyproject.toml`, `backend/uv.lock` (`scipy==<última estable compatible con Python 3.13>`, también `scipy-stubs` si mypy lo requiere)
- Create: `backend/app/modules/validation/domain/parameters.py`, `backend/app/modules/validation/domain/agreement.py`
- Test: `backend/tests/unit/test_validation_agreement.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) ZoneRanking(zone_id: int, concentration: Concentration, motor_order: Mapping[UUID, int], evaluator_orders: Mapping[UUID, Mapping[UUID, int]])` — `Concentration` es un `StrEnum` (`HIGH="alta"`, `LOW="baja"`) en `validation/domain/zones.py` (lo crea esta tarea).
  - `@dataclass(frozen=True) Correlation(coefficient: float, p_value: float)`
  - `@dataclass(frozen=True) ZoneAgreement(zone_id, n_reports, n_evaluators, panel_order: Mapping[UUID, float], spearman: Correlation, kendall: Correlation, per_evaluator: Mapping[UUID, tuple[Correlation, Correlation]], kendall_w: KendallW | None, within_one_pct: float, disagreement: Mapping[UUID, float])` con `KendallW(w: float, chi2: float, p_value: float)`.
  - `@dataclass(frozen=True) BetweenZones(test: Literal["mann_whitney", "kruskal_wallis"], statistic: float, p_value: float, significant: bool)`.
  - `zone_agreement(ranking: ZoneRanking) -> ZoneAgreement | None` (None si ningún evaluador envió).
  - `between_zones(agreements: Sequence[tuple[Concentration, ZoneAgreement]]) -> BetweenZones | NotComputable` con `NotComputable(reason: str)`; dos zonas → Mann-Whitney bilateral entre los desacuerdos; tres → Kruskal-Wallis; menos de una `alta` y una `baja` → `NotComputable("Se necesita al menos una zona de alta y una de baja concentración con órdenes")`.
- Algoritmo que el test no determina: `panel_order` = `scipy.stats.rankdata(media de posiciones por reporte, method="average")`; desacuerdo = `abs(motor - panel) / (n - 1)`; coincidencia ±1 = % de reportes con `abs(motor - panel) <= 1`; W de Kendall = `12·S / (m²(n³ − n))` con S la suma de cuadrados de las desviaciones de las sumas de rangos, chi² = `m(n − 1)W`, p de chi² con `n − 1` gl (sin corrección por empates: los evaluadores no empatan); solo con m ≥ 2. Spearman `scipy.stats.spearmanr`, Kendall `scipy.stats.kendalltau` (tau-b).

- [ ] **Step 1: pruebas** — `test_identical_orders_give_perfect_agreement` (rho = 1, tau = 1, ±1 = 100, desacuerdos = 0); `test_reversed_order_gives_minus_one` (n = 5, rho = −1, tau = −1); `test_panel_order_averages_evaluators` (dos evaluadores [1,2,3,4,5] y [2,1,3,4,5] → panel {a:1.5, b:1.5, c:3, d:4, e:5}); `test_kendall_w_perfect_agreement_is_one` (3 evaluadores iguales, W = 1.0); `test_kendall_w_needs_two_evaluators` (uno → `kendall_w is None`); `test_within_one_counts_neighbors` (motor [1..6], panel desplazado una posición → 100; un reporte a 3 posiciones → 83.33…); `test_zone_without_orders_is_none`; `test_two_zones_use_mann_whitney` y `test_three_zones_use_kruskal_wallis` (comparar estadístico y p con llamadas directas a `scipy.stats.mannwhitneyu(..., alternative="two-sided")` / `kruskal` sobre los mismos desacuerdos); `test_between_zones_requires_high_and_low` (dos zonas `alta` → `NotComputable`); `test_significance_uses_alpha` (p = 0.049 → True, p = 0.05 → False, usando un doble del cálculo o datos elegidos).
- [ ] **Step 2:** `uv run pytest tests/unit/test_validation_agreement.py` → FALLA.
- [ ] **Step 3:** Añadir `scipy` con `uv add scipy==X.Y.Z`; implementar `parameters.py`, `zones.py` (solo `Concentration` por ahora) y `agreement.py`.
- [ ] **Step 4:** Pruebas → PASAN; `uv run mypy`, `ruff`, `uv run pip-audit` (o el comando de auditoría de la CI) limpios.
- [ ] **Step 5:** Commit `feat(validation): métricas de acuerdo entre rankings (propuesta 114)`.

### Task 3: Zonas — `zones-import`, zona del reporte y `GET /admin/zones`

**Files:**
- Modify: `backend/app/modules/validation/domain/zones.py` (lectura y validación del GeoJSON)
- Create: `backend/app/modules/validation/domain/ports.py`, `backend/app/modules/validation/application/import_zones.py`, `backend/app/modules/validation/infrastructure/zone_repository.py`
- Create: `backend/app/modules/validation/presentation/admin_router.py`, `schemas.py`, `dependencies.py`
- Modify: `backend/app/cli.py` (comando `zones-import RUTA`), `backend/app/main.py` (incluir routers del módulo)
- Modify: `backend/app/modules/reports/infrastructure/repository.py` (`SqlReportRepository.add` asigna `id_zona` con subconsulta `ST_Covers`)
- Test: `backend/tests/unit/test_validation_zones.py`, `backend/tests/integration/test_zones_api.py`, `backend/tests/unit/test_cli.py`

**Interfaces:**
- Produces: `ZoneDefinition(name: str, concentration: Concentration, polygon_geojson: dict)`; `parse_zones(geojson: Mapping[str, Any]) -> list[ZoneDefinition]` que lanza `InvalidZonesError(message)`; `ZoneRepository` (Protocol) con `upsert(zones: Sequence[ZoneDefinition]) -> None` (valida en SQL con `ST_IsValid` y que no se solapen con `ST_Overlaps`/`ST_Intersects` de interiores, lanza `InvalidZonesError`), `assign_reports() -> int`, `list_with_counts() -> list[ZoneSummary]` con `ZoneSummary(id, name, concentration, active_reports, total_reports, geometry_geojson)`; `ImportZones.execute(geojson) -> ImportZonesResult(zones: int, reports_assigned: int)` en una sola transacción.
- `GET /api/v1/admin/zones` → `{"items": [{"id", "name", "concentration", "active_reports", "total_reports", "geometry"}]}` con la geometría simplificada (`ST_SimplifyPreserveTopology` a ~5 m, en grados ≈ 0.00005).
- CLI: `python -m app.cli zones-import docs/validacion/zonas.geojson` imprime `Zonas cargadas: N · reportes asignados: M`; con error imprime el mensaje y sale con código 1.

- [ ] **Step 1: pruebas unitarias** de `parse_zones`: acepta FeatureCollection con 2 Polygon y propiedades `name`/`concentration`; rechaza (con mensaje en español que nombra la zona) `MultiPolygon`, falta de `name`, `concentration` distinta de `alta`/`baja`, nombres repetidos, colección vacía, más de 3 zonas (la tesis pide 2 a 3: `MAX_ZONES = 3` en `parameters.py`). Prueba de CLI que el comando llama al caso de uso y sale con 1 ante `InvalidZonesError`.
- [ ] **Step 2: pruebas de integración**: importar dos zonas asigna `id_zona` a los reportes que caen dentro y deja NULL los de fuera; reimportar con el mismo nombre reemplaza geometría y concentración (idempotente); polígonos solapados → nada cambia; geometría auto-intersecada → error; crear un reporte (`POST /reports`) dentro de una zona deja su `id_zona`; `GET /admin/zones` cuenta activos y totales y exige administrador (403 a ciudadano y a evaluador).
- [ ] **Step 3:** Correr → FALLA. **Step 4:** Implementar. **Step 5:** `test-integration.sh` → PASA; mypy y ruff limpios.
- [ ] **Step 6:** Commit `feat(validation): cargar zonas desde GeoJSON y asignar su zona a los reportes`.

### Task 4: Cuentas de evaluador y acceso por rol

**Files:**
- Create: `backend/app/modules/auth/application/create_staff.py` (generaliza `create_admin.py`; dejar `CreateAdmin` como alias o reemplazar sus usos)
- Modify: `backend/app/cli.py` (`create-evaluator --name --email`), `backend/app/modules/auth/application/login.py` (`required_role` → `allowed_roles: frozenset[UserRole] | None` en login y refresco), `backend/app/modules/auth/presentation/web_router.py` (permitir `{ADMIN, EVALUATOR}`; el código `ADMIN_ROLE_REQUIRED` pasa a `STAFF_ROLE_REQUIRED` con mensaje «Esta cuenta no tiene acceso al panel.»), `backend/app/modules/auth/presentation/dependencies.py` (`require_evaluator`, `EvaluatorUserDep`), `backend/app/modules/reports/presentation/router.py` y `backend/app/modules/confirmations/presentation/router.py` (403 `EVALUATOR_CANNOT_REPORT` si el usuario es evaluador)
- Test: `backend/tests/unit/test_auth_application.py`, `backend/tests/integration/test_web_session_api.py` (o el archivo existente de la sesión web), `test_reports_api.py`, `test_confirmations_api.py`, `test_cli.py`

**Interfaces:**
- Produces: `require_evaluator(user) -> User` (403 `FORBIDDEN` si no es evaluador); `EvaluatorUserDep`; `CreateStaffAccount.execute(name, email, password, role: UserRole) -> uuid.UUID` (rechaza `CITIZEN`).
- `GET /api/v1/me` ya devuelve `role`; el panel lo usará (Tarea 10).

- [ ] **Step 1: pruebas** — login web de evaluador → 200 con cookies; de ciudadano → 403 `STAFF_ROLE_REQUIRED`; refresco web de una cuenta que pasó a ciudadano → revoca y 403; `require_evaluator` rechaza a administrador y ciudadano; evaluador en `POST /reports` y en `POST /reports/{id}/confirmations` → 403 `EVALUATOR_CANNOT_REPORT` (sin consumir cupo); `create-evaluator` crea la cuenta con rol `evaluador` y pide la contraseña sin eco como `create-admin`.
- [ ] **Step 2:** Correr → FALLA. **Step 3:** Implementar; actualizar las pruebas existentes que esperan `ADMIN_ROLE_REQUIRED` y el cliente del panel que lo lea (`admin-web/src/auth/` — buscar el código con grep y cambiarlo en esta misma tarea para no romper la CI del panel).
- [ ] **Step 4:** Pruebas del backend y `cd admin-web && npm test` → PASAN.
- [ ] **Step 5:** Commit `feat(auth): cuentas de evaluador con acceso al panel`.

### Task 5: Rondas — abrir, avance y cerrar

**Files:**
- Create: `backend/app/modules/validation/domain/rounds.py`, `backend/app/modules/validation/application/manage_rounds.py`, `backend/app/modules/validation/infrastructure/round_repository.py`
- Modify: `validation/presentation/admin_router.py`, `schemas.py`, `dependencies.py`
- Test: `backend/tests/unit/test_validation_rounds.py`, `backend/tests/integration/test_evaluation_rounds_api.py`

**Interfaces:**
- Consumes: `priority/domain/ranking.py::ranking_key`; `ZoneRepository.list_with_counts`.
- Produces: `RoundCandidate(report_id, zone_id, urgency_score: Decimal, severity, confirmations, created_at)` (cumple `Rankable`); `sample_and_rank(candidates: Sequence[RoundCandidate], sample_size: int, seed: int) -> list[RoundEntry]` con `RoundEntry(report_id, zone_id, urgency_score, motor_order)` — por zona: si hay más de `sample_size`, `random.Random(seed + zone_id).sample(ordenados por id, sample_size)`; luego ordenar con `(ranking_key(c), c.report_id)` y numerar 1..n; lanza `ZoneTooSmallError(zone_name, count)` si alguna zona tiene menos de `MIN_REPORTS_PER_ZONE`. `OpenRound.execute(name, sample_size, admin_id) -> uuid.UUID` (semilla con `secrets.randbits(31)`, `id_config` = versión vigente, lanza `RoundAlreadyOpenError`, `NoZonesError`); `CloseRound.execute(round_id)` (lanza `RoundNotFoundError`, `RoundAlreadyClosedError`); `RoundProgress(round_id, name, status, sample_size, opened_at, closed_at, zones: list[ZoneProgress(zone_id, name, concentration, n_reports, submitted_by: list[EvaluatorLabel])])`.
- Rutas (sección 10 del diseño): `POST /admin/evaluation-rounds` (`{"name", "sample_size"}`, 1–100) → 201 `{"id"}`; 409 `EVALUATION_ROUND_ALREADY_OPEN`; 422 `EVALUATION_ZONE_TOO_SMALL` con `details: {"zone", "reports", "minimum"}`; 422 `EVALUATION_NO_ZONES`; `GET /admin/evaluation-rounds` (más reciente primero, `limit/offset`, tope 50); `GET /admin/evaluation-rounds/{id}`; `POST /admin/evaluation-rounds/{id}/close` → 200; 409 `EVALUATION_ROUND_CLOSED`; 404 `EVALUATION_ROUND_NOT_FOUND`. En el avance, los evaluadores salen como etiqueta «Evaluador k», no por nombre.

- [ ] **Step 1: pruebas unitarias** de `sample_and_rank`: misma semilla → mismo resultado; muestra de tamaño n por zona; zona con menos de n pero ≥ 5 entra completa; zona con 4 → `ZoneTooSmallError`; orden por U, luego severidad, confirmaciones, antigüedad; **empate total → desempate por `report_id`** (Review Focus 4).
- [ ] **Step 2: pruebas de integración**: abrir congela solo reportes activos dentro de zonas, con su U y la versión de pesos; cambiar los pesos después no cambia `ronda_reporte`; segunda apertura → 409; **apertura concurrente** simulada insertando una ronda abierta entre la verificación y el INSERT (o dos sesiones) → 409, no 500 (Review Focus 3); cerrar dos veces → 409; rutas exigen administrador.
- [ ] **Step 3:** Correr → FALLA. **Step 4:** Implementar (traducir el `IntegrityError` de `uq_ronda_abierta` a `RoundAlreadyOpenError`, como hace `SqlConfirmationRepository`). **Step 5:** → PASA; mypy, ruff.
- [ ] **Step 6:** Commit `feat(validation): rondas de evaluación con reportes congelados`.

### Task 6: Evaluación a ciegas (rutas del evaluador)

**Files:**
- Create: `backend/app/modules/validation/domain/blind.py`, `backend/app/modules/validation/application/blind_evaluation.py`, `backend/app/modules/validation/infrastructure/blind_reader.py`, `backend/app/modules/validation/presentation/evaluator_router.py`
- Test: `backend/tests/unit/test_validation_blind.py`, `backend/tests/integration/test_blind_evaluation_api.py`

**Interfaces:**
- Consumes: `EvaluatorUserDep`; `PhotoReader` y `PhotoKeys` de `reports` para las fotos.
- Produces: `BlindCard(report_id, description: str | None, road_name: str | None, severity, location: GeoPoint, nearby_services: list[ServicePoint(name, type, location)])` — **sin ningún otro campo**; `shuffle_for(report_ids, round_seed: int, evaluator_id: UUID) -> list[UUID]` (orden por `random.Random(f"{round_seed}:{evaluator_id}")` sobre la lista ordenada por id); `SubmitOrder.execute(evaluator_id, zone_id, report_ids: Sequence[UUID])` que valida que sea exactamente el conjunto de la zona en la ronda abierta, sin repetidos (`InvalidOrderError`), que no haya enviado ya (`OrderAlreadySubmittedError`) y guarda posiciones 1..n.
- Rutas: `GET /evaluation/current` → `{"round": {"id", "name"}, "zones": [{"id", "name", "n_reports", "submitted": bool}]}` o 404 `EVALUATION_NO_OPEN_ROUND`; `GET /evaluation/current/zones/{zone_id}` → `{"zone": {...}, "cards": [BlindCard en el orden de shuffle_for], "submitted": bool}`; `GET /evaluation/current/reports/{report_id}/photo` y `/thumbnail` (404 `PHOTO_NOT_AVAILABLE` si el reporte no está en la ronda abierta o no tiene foto); `PUT /evaluation/current/zones/{zone_id}/order` (`{"report_ids": [...]}`) → 201; 409 `EVALUATION_ORDER_ALREADY_SUBMITTED`; 422 `EVALUATION_ORDER_INVALID`. La ubicación de la tarjeta es la **exacta** (el evaluador es parte del equipo de la prueba, como el administrador), pero ni la tarjeta ni ninguna ruta del evaluador incluye los campos prohibidos de las Global Constraints.

- [ ] **Step 1: pruebas** — las claves de cada tarjeta son exactamente `{"report_id", "description", "road_name", "severity", "location", "nearby_services"}` (prueba que falla si aparece cualquier otra); dos evaluadores ven órdenes iniciales distintos y estables entre llamadas; **Review Focus 1**: evaluador en `/admin/zones`, `/admin/evaluation-rounds` y `/reports/{id}/photo` → 403/404, foto de un reporte fuera de la ronda → 404, ciudadano y administrador en `/evaluation/current` → 403; **Review Focus 2**: orden con un id repetido, con uno faltante, con uno de otra zona, vacío → 422 y `orden_evaluador` sigue vacío; segundo envío → 409; envío con la ronda cerrada → 404 `EVALUATION_NO_OPEN_ROUND`.
- [ ] **Step 2:** Correr → FALLA. **Step 3:** Implementar. **Step 4:** → PASA; mypy, ruff.
- [ ] **Step 5:** Commit `feat(validation): vista a ciegas y envío del orden del evaluador`.

### Task 7: Registro de avisos de duplicado

**Files:**
- Create: `backend/app/modules/validation/domain/warnings.py`, `backend/app/modules/validation/infrastructure/warning_repository.py`
- Modify: `backend/app/modules/reports/domain/ports.py` (puerto `DuplicateWarningRecorder`), `backend/app/modules/reports/application/find_nearby.py`, `backend/app/modules/reports/application/create_report.py`, `backend/app/modules/reports/domain/duplicates.py` (`PossibleDuplicateError.warning_id`), `backend/app/modules/reports/presentation/router.py`, `schemas.py`, `dependencies.py`; `backend/app/modules/confirmations/application/confirm_report.py`, `presentation/schemas.py`, `router.py`, `dependencies.py`
- Test: `backend/tests/unit/test_create_report.py`, `test_confirm_report.py`, `backend/tests/integration/test_duplicate_warnings_api.py`

**Interfaces:**
- Produces: `DuplicateWarningRecorder` (Protocol, en `reports/domain/ports.py` para que `reports` no dependa de `validation`): `record(user_id: UUID, location: GeoPoint, candidates: Sequence[DuplicateCandidate]) -> UUID` (guarda la zona por `ST_Covers`, no el punto) y `resolve(warning_id: UUID, user_id: UUID, decision: Literal["confirmo", "creo_igual"], report_id: UUID) -> bool` (solo si el aviso es del usuario y está `pendiente`; para `confirmo`, además el reporte debe estar entre los candidatos; devuelve False si no aplica, sin error). Implementación en `validation/infrastructure/warning_repository.py`.
- `FindPossibleDuplicates.execute` registra un aviso cuando hay candidatos y confirma la transacción; devuelve `(candidates, warning_id | None)`. `NearbyReportsResponse` gana `duplicate_warning_id: UUID | None`.
- `CreateReport`: en la **primera** verificación (sin candado) registra el aviso, confirma y lanza `PossibleDuplicateError(candidates, warning_id)`; el 409 incluye `details.duplicate_warning_id`. La segunda verificación (con candado, carrera rara) no registra: documentarlo en un comentario. `ReportSubmission.duplicate_warning_id: UUID | None`; con `create_anyway` y un id, tras crear llama `resolve(..., "creo_igual", nuevo_id)` en la misma transacción. Campo de formulario `duplicate_warning_id` opcional.
- `ConfirmReport.execute(report_id, user_id, location, duplicate_warning_id: UUID | None = None)`: tras guardar la confirmación llama `resolve(..., "confirmo", report_id)` en la misma transacción. `ConfirmationRequest.duplicate_warning_id: UUID | None = None`.
- Un aviso inválido, ajeno o ya resuelto nunca rompe la acción del ciudadano.

- [ ] **Step 1: pruebas** — `nearby` con candidatos crea un aviso `pendiente` con su zona y candidatos y devuelve su id; sin candidatos no crea nada y devuelve `null`; el 409 crea un aviso y trae el id; crear con `create_anyway` + id → `creo_igual` con el reporte nuevo; confirmar con id → `confirmo` con ese reporte; id de otro usuario, de un reporte que no era candidato o ya resuelto → la acción funciona y el aviso no cambia; un reintento idempotente de `POST /reports` no crea avisos nuevos.
- [ ] **Step 2:** FALLA. **Step 3:** Implementar. **Step 4:** `test-integration.sh` completo → PASA; mypy, ruff.
- [ ] **Step 5:** Commit `feat(reports): registrar los avisos de posible duplicado y su decisión`.

### Task 8: Resultados y exportación de la ficha

**Files:**
- Create: `backend/app/modules/validation/application/round_results.py`, `backend/app/modules/validation/infrastructure/results_reader.py`, `backend/app/modules/validation/presentation/csv_export.py`
- Modify: `validation/presentation/admin_router.py`, `schemas.py`
- Test: `backend/tests/unit/test_validation_results.py`, `backend/tests/unit/test_validation_csv.py`, `backend/tests/integration/test_round_results_api.py`

**Interfaces:**
- Consumes: `zone_agreement`, `between_zones` (Tarea 2); tablas de las Tareas 1, 5, 6 y 7 (avisos).
- Produces: `RoundResults(round, zones: list[ZoneResult(zone, agreement: ZoneAgreement | None, dedup: DedupSummary(reports, reports_confirmed, confirmations, warnings_total, warnings_confirmed, warnings_created_anyway, warnings_pending))], between: BetweenZones | NotComputable)`.
- Rutas: `GET /admin/evaluation-rounds/{id}/results` → JSON con todo lo anterior (409 `EVALUATION_ROUND_STILL_OPEN` si está abierta); `GET /admin/evaluation-rounds/{id}/export/ficha.csv` (columnas: `id_reporte,zona,concentracion,puntaje_u,orden_motor,orden_panel,desacuerdo,coincide_pm1,evaluador_1,…`), `resumen.csv` (una fila por zona con n, evaluadores, rho, p, tau, p, W, p, ±1 %, y una fila final con la prueba entre zonas), `reportes.csv` (`id_reporte,zona,fecha_creacion,via,estado,confirmaciones,foto` donde `foto` es la ruta relativa de la API), `avisos.csv` (`id_aviso,zona,fecha,decision,id_reporte_resultante,candidatos` con los candidatos `id:distancia` separados por `;`). `Content-Disposition: attachment; filename="ronda-<nombre-slug>-ficha.csv"`. Las cuatro exportaciones también exigen ronda cerrada salvo `reportes.csv` y `avisos.csv`, que sirven para la revisión manual y se permiten siempre.

- [ ] **Step 1: pruebas** — con una ronda de prueba de 2 zonas × 5 reportes y 2 evaluadores sembrada en la base, `results` coincide con llamar a `zone_agreement` sobre los mismos datos; zona sin órdenes → `agreement: null` y fuera de la prueba entre zonas; CSV con BOM, punto decimal, evaluadores como `evaluador_1…`, sin nombres ni correos (buscar el correo del evaluador en el texto → ausente); abierta → 409.
- [ ] **Step 2:** FALLA. **Step 3:** Implementar. **Step 4:** PASA; mypy, ruff.
- [ ] **Step 5:** Commit `feat(validation): resultados de la ronda y ficha comparativa en CSV`.

### Task 9: Cierre de la entrega 1

**Files:** `README.md` (sección del objetivo 4: `zones-import`, `create-evaluator`, flujo de ronda, exportaciones), `AGENTS.md` (6.2: endpoints nuevos; 2.1: tablas nuevas; estado), `CHANGELOG.md` (Sin publicar), `docs/bitacora.md` (fila de implementación con pruebas; decisión menor `scipy`), `docs/adr/0008-validacion-panel-referencia.md` (rondas congeladas, vista a ciegas, métricas, avisos), `docs/validacion/README.md` (formato del GeoJSON con un ejemplo de dos zonas ficticias claramente marcado como ejemplo).

- [ ] **Step 1:** Escribir la documentación.
- [ ] **Step 2:** `infra/scripts/test-integration.sh --cov` (cobertura ≥ 80 % en `validation/domain` y `validation/application`), `uv run mypy`, `uv run ruff check .`, `uv run ruff format --check .`.
- [ ] **Step 3:** Commit `docs: documentar la herramienta del objetivo 4 (backend)`; integrar en `main` con `--no-ff`, push, verificar la CI, borrar la rama; actualizar Linear (ARE-22).

---

## Entrega 2 — panel y app (rama `feat/validation-panel`)

### Task 10: Sesión por rol en el panel

**Files:**
- Modify: `admin-web/src/api/schema.d.ts` (`npm run gen:api` contra la API de la entrega 1), `admin-web/src/auth/SessionProvider.tsx` (guardar `role` de `/me`), `admin-web/src/auth/RequireAdmin.tsx` → `RequireRole.tsx` (`<RequireRole role="administrador" | "evaluador">`), `admin-web/src/app/router.tsx`, `admin-web/src/app/Layout.tsx` (menú «Comparación» para administrador; menú mínimo «Mis evaluaciones» para evaluador)
- Test: `RequireRole.test.tsx`, `session.test.ts`, `router` (prueba de rutas por rol)

**Interfaces:**
- Produces: `useSession().user: { name: string; role: "administrador" | "evaluador" } | null`; `HOME_PATH` por rol (`/priorizacion` o `/evaluacion`); rutas `/comparacion` (administrador) y `/evaluacion`, `/evaluacion/zonas/:zoneId` (evaluador).

- [ ] **Step 1:** Pruebas: un evaluador que entra a `/priorizacion` es llevado a `/evaluacion`; un administrador que entra a `/evaluacion` es llevado a `/priorizacion`; el menú del evaluador no muestra Priorización, Pesos ni Comparación; el error `STAFF_ROLE_REQUIRED` muestra «Esta cuenta no tiene acceso al panel.».
- [ ] **Step 2:** FALLA. **Step 3:** Implementar. **Step 4:** `npm run lint && npm run typecheck && npm test` → PASA.
- [ ] **Step 5:** Commit `feat(admin-web): sesión y rutas por rol (administrador y evaluador)`.

### Task 11: Administrador — Zonas y Rondas

**Files:**
- Create: `admin-web/src/features/validation/api.ts`, `ZonesMap.tsx`, `RoundsPanel.tsx`, `OpenRoundForm.tsx`, `ComparisonPage.tsx` (contenedor con pestañas Zonas · Rondas · Resultados), `validation.css`, `fixtures.ts`
- Test: `ZonesMap.test.tsx`, `RoundsPanel.test.tsx`, `OpenRoundForm.test.tsx`

**Interfaces:**
- Consumes: rutas de las Tareas 3 y 5.
- Produces: `ComparisonPage` en `/comparacion`; hooks `useZones()`, `useRounds()`, `useRound(id)`, `useOpenRound()`, `useCloseRound(id)` (TanStack Query, invalidan `["rounds"]`).
- Contenido: mapa con los polígonos (color por concentración, leyenda con texto, atribución OSM) y tabla de zonas con conteos; formulario «Abrir ronda» (nombre, tamaño de muestra 1–100) que muestra los 409/422 con su mensaje y, para `EVALUATION_ZONE_TOO_SMALL`, la zona y cuántos reportes tiene; avance por zona y evaluador; «Cerrar ronda» con confirmación («Ya no se aceptarán órdenes»). Seguir el Figma «Panel · Comparación con el panel de referencia» y los tokens.

- [ ] **Step 1:** Pruebas con MSW: estados de carga, vacío («Aún no hay zonas: cárgalas con `zones-import`») y error con reintento; abrir ronda envía `{name, sample_size}` y refresca; el 422 muestra la zona; cerrar pide confirmación y deshabilita el doble envío.
- [ ] **Step 2:** FALLA. **Step 3:** Implementar. **Step 4:** lint, typecheck, test → PASA.
- [ ] **Step 5:** Commit `feat(admin-web): zonas y rondas de evaluación`.

### Task 12: Evaluador — Mis evaluaciones y vista a ciegas

**Files:**
- Modify: `admin-web/package.json` (`@dnd-kit/core`, `@dnd-kit/sortable`, versiones exactas)
- Create: `admin-web/src/features/evaluation/api.ts`, `MyEvaluationsPage.tsx`, `BlindZonePage.tsx`, `SortableCard.tsx`, `useDraftOrder.ts`, `evaluation.css`
- Test: `MyEvaluationsPage.test.tsx`, `BlindZonePage.test.tsx`, `useDraftOrder.test.ts`

**Interfaces:**
- Consumes: rutas de la Tarea 6; `AuthImage` (ya existe) para las fotos con la ruta del evaluador.
- Produces: `useDraftOrder(roundId, zoneId, initialIds) -> { ids, moveUp(id), moveDown(id), move(from, to), reset() }` persistido en `sessionStorage` con clave `evaluation:${roundId}:${zoneId}`; descarta el borrador si el conjunto de ids no coincide con el del servidor.
- Contenido: lista de zonas con «Pendiente / Enviada»; vista a ciegas como el boceto de la sección 6 del diseño: tarjetas con foto, descripción, vía, chip de severidad (componente existente), botones «Subir» / «Bajar» con `aria-label` que nombran la vía y anuncio en región viva («Carrera 27, ahora en la posición 2 de 12»), arrastre con `@dnd-kit` y soporte de teclado; minimapa en un panel lateral al pulsar «Ver en el mapa» con el punto y los servicios críticos; «Enviar este orden» con confirmación «No podrás cambiarlo»; tras enviar vuelve a la lista con aviso de éxito. Sin conexión o error: mensaje y reintento, el borrador se conserva.

- [ ] **Step 1:** Pruebas: el orden inicial es el del servidor; subir/bajar cambia el orden y lo anuncia; recargar conserva el borrador; enviar manda `report_ids` en el orden visible; 409 muestra «Ya enviaste esta zona»; la página nunca renderiza «U», «puntaje», «confirmaciones» ni «orden del motor» (buscar en el DOM).
- [ ] **Step 2:** FALLA. **Step 3:** Implementar. **Step 4:** lint, typecheck, test → PASA; `npm audit --audit-level=high` limpio.
- [ ] **Step 5:** Commit `feat(admin-web): vista a ciegas para evaluadores`.

### Task 13: Administrador — Resultados y exportación

**Files:**
- Create: `admin-web/src/features/validation/ResultsPanel.tsx`, `ZoneAgreementCard.tsx`, `BetweenZonesCard.tsx`, `DedupTable.tsx`, `exportLinks.ts`
- Test: `ResultsPanel.test.tsx`

**Interfaces:**
- Consumes: `GET /admin/evaluation-rounds/{id}/results` y las cuatro exportaciones (Tarea 8).
- Contenido: por zona, rho, tau, W (o «Se necesitan al menos 2 evaluadores»), coincidencia ±1, n y evaluadores; tarjeta de la prueba entre zonas con estadístico, p y «Diferencia significativa con α = 0,05: Sí/No», o el motivo de `NotComputable`; tabla de deduplicación por zona; botones de descarga de los cuatro CSV (descarga con `fetch` autenticado y `Blob`, porque la sesión va en cookie con CSRF). Decimales con coma. Ronda abierta → «Los resultados se muestran al cerrar la ronda». Texto fijo bajo los resultados: «Estos valores describen la ronda; la interpretación de las hipótesis se hace en la tesis.»

- [ ] **Step 1:** Pruebas con MSW: muestra coma decimal; `NotComputable` muestra su motivo; ronda abierta no pide resultados; descarga crea un enlace con el nombre de archivo del servidor.
- [ ] **Step 2:** FALLA. **Step 3:** Implementar. **Step 4:** lint, typecheck, test → PASA.
- [ ] **Step 5:** Commit `feat(admin-web): resultados de la ronda y ficha comparativa`.

### Task 14: App — enviar el aviso de duplicado

**Files:**
- Modify: `mobile/lib/features/report_new/domain/nearby_report.dart` (o un nuevo `duplicate_warning.dart`), `data/http_new_report_repository.dart` (leer `duplicate_warning_id` de `nearby` y del 409; enviarlo en `create` y en `confirm`), `domain/new_report_repository.dart`, `domain/report_draft.dart` y `application/report_draft_controller.dart` (guardar el id en el borrador), `application/submit_report_controller.dart`
- Test: `mobile/test/features/report_new/http_new_report_repository_test.dart`, `submit_report_controller_test.dart`, `test/support/fake_new_report_repository.dart`

**Interfaces:**
- Produces: `NewReportRepository.nearby(GeoFix) -> Future<NearbyResult>` con `NearbyResult(candidates: List<NearbyReport>, warningId: String?)`; `create(draft, {idempotencyKey, createAnyway, String? duplicateWarningId})`; `confirm(reportId, fix, {String? duplicateWarningId})`; `PossibleDuplicates` lleva el `warningId`.
- La confirmación desde el mapa no manda id (no hubo aviso).

- [ ] **Step 1:** Pruebas: `nearby` devuelve el id; el 409 se convierte en `PossibleDuplicates` con id; «Crear de todos modos» manda `duplicate_warning_id` en el formulario; «Es el mismo daño: confirmarlo» lo manda en el cuerpo; sin id (respuesta antigua) todo sigue funcionando.
- [ ] **Step 2:** FALLA. **Step 3:** Implementar. **Step 4:** `dart format --set-exit-if-changed lib test`, `flutter analyze`, `flutter test` → PASA.
- [ ] **Step 5:** Commit `feat(mobile): enviar el aviso de duplicado con la decisión del ciudadano`.

### Task 15: Punta a punta, tesis y cierre

**Files:**
- Create: `admin-web/e2e/validation.spec.ts`; Modify: `infra/scripts/e2e-panel.sh` (crear dos zonas de prueba, un evaluador y reportes en el stack aparte)
- Modify: tesis `C:\Users\areva\Documents\trabajo_grado\CTG_Noviembre_SantiagoArevalo.docx` (respaldo previo con fecha), `README.md`, `AGENTS.md` (estado), `CHANGELOG.md`, `docs/bitacora.md`, `mobile/README.md` (lista de prueba en el celular: el aviso queda registrado al confirmar y al crear de todos modos)

- [ ] **Step 1:** E2E: el administrador abre una ronda; el evaluador inicia sesión, ordena una zona con el teclado y la envía; el administrador cierra y ve los resultados y descarga `ficha.csv`. `infra/scripts/e2e-panel.sh` → PASA.
- [ ] **Step 2:** Tesis (sección 12 del diseño): en 2.3 (nota), 3.4 (criterio de HU-09), 3.7 y 4.4 reemplazar «porcentaje de coincidencia» por las medidas de la propuesta 114, añadir las columnas de la ficha, describir la ronda congelada, la vista a ciegas y el registro de avisos (y que mide desde su activación). Editar `word/document.xml` párrafo por párrafo como en la propuesta 112, verificando que el .docx abre.
- [ ] **Step 3:** Documentación y bitácora; CI completa en verde; integrar en `main` con `--no-ff`, borrar la rama; Linear ARE-22 y ARE-41 al día. Recordar al responsable: ER de Lucid (cinco tablas nuevas, `zona.concentracion`, rol `evaluador`; el conector solo tiene lectura) y que la prueba piloto requiere reportes reales y el panel definido.
