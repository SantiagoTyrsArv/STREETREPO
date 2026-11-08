# Panel administrativo (objetivo 3) — plan de implementación

> **Para agentes:** SUB-SKILL REQUERIDA: usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para ejecutar este plan tarea por tarea. Los pasos usan casillas (`- [ ]`).

**Objetivo:** construir el panel web de la Secretaría (inicio de sesión de funcionarios, Priorización, Detalle y estado, Pesos del modelo) y el backend `/admin` que necesita, ejecutable en el equipo del responsable con `docker compose up` y con datos de demostración.

**Arquitectura:** el backend gana un módulo de lectura administrativa (ranking, resumen, mapa de calor, detalle), un caso de uso de cambio de estado, rutas de pesos sobre `UpdateWeights` y una variante web de la sesión (decisión 42). El panel es una SPA React + TypeScript en `admin-web/`, servida por nginx en su propio origen y que habla con la API por CORS con credenciales.

**Stack:** FastAPI, SQLAlchemy 2, PostGIS, pytest · Vite, React 18, TypeScript strict, TanStack Query, React Router, react-leaflet + leaflet.heat + leaflet.markercluster, openapi-typescript, Vitest + Testing Library + MSW, Playwright · nginx (imagen sin root).

**Spec:** `docs/superpowers/specs/2026-11-08-panel-administrativo-objetivo-3-design.md` (leerla junto con este plan). Reglas del proyecto: `AGENTS.md`.

## Restricciones globales

- Todas las rutas nuevas bajo `/api/v1/admin/` dependen de `require_admin` (`app/modules/auth/presentation/dependencies.py`). Errores con el formato uniforme `AppError(code, message, status, details)`.
- Capas de la guía 4.2: router → caso de uso → dominio ← repositorio. Sin SQL en routers. Consultas parametrizadas, sin `SELECT *`, paginación `limit` (por defecto 20, máximo 100) y `offset`.
- Orden del ranking = `priority/domain/ranking.py::ranking_key`: U desc → severidad desc → confirmaciones desc → `fecha_creacion` asc; como último criterio, `id_reporte` asc (solo para paginar de forma estable).
- «Activo» = todo estado salvo `reparado` (decisión 13).
- Indicadores del encabezado: **Activos · Evaluados · Priorizados · Reparados** (propuesta 75).
- Sesión web (decisión 42, ADR 0004): acceso en memoria del navegador; refresco en cookie `sr_refresh`, `HttpOnly`, `Secure`, `SameSite=Strict`, `Path=/api/v1/auth/web`; cabecera anti-CSRF `X-CSRF-Protection: 1` obligatoria en las rutas web de sesión; `Origin` debe estar en `CORS_ORIGINS`. Nunca `localStorage`.
- Interfaz en español de Colombia; decimales con coma (`8,70`); fechas en `America/Bogota`, formato corto `13 oct` (y `13 oct, 4:05 p. m.` en el historial). Colores y tipografías solo desde los tokens de la guía 10.1. Chips con texto. Atribución de OpenStreetMap en todo mapa; URL de *tiles* por `VITE_TILE_URL`.
- El panel no calcula U, transiciones ni el orden: muestra lo que da la API (las transiciones permitidas vienen en `allowed_next_statuses`).
- Versiones exactas en `package.json` (`save-exact=true` en `admin-web/.npmrc`); TypeScript `strict`.
- Ramas: una por grupo indicado en cada tarea (`feat/…`, `chore/…`), Conventional Commits con cuerpo (qué, por qué, verificación) y `Refs: HU-xx`; integrar con `git merge --no-ff` a `main` sin PR; antes de integrar, `ruff`, `ruff format --check`, `mypy`, `pytest` (backend) y `npm run lint`, `npm run typecheck`, `npm test` (panel) en verde.

## Foco de revisión

1. **El acceso vence a los 15 min con varias peticiones en curso:** todas reciben 401; el panel debe hacer **un solo** refresco, reintentar cada una una vez y, si el refresco falla, volver al inicio de sesión con «Tu sesión terminó. Inicia sesión de nuevo.» (prueba en la tarea 7).
2. **Pesos escritos como `0,5`, con tres decimales o que suman 0,99:** el formulario acepta coma, bloquea guardar y explica por qué; el servidor responde 422 si llegan igual (pruebas en las tareas 4 y 10).
3. **Reporte sin vía, sin servicio crítico a 500 m o aún sin evaluación:** el detalle muestra «Sin vía asociada», «Ningún servicio crítico a menos de 500 m» o «Pendiente de evaluación» sin romperse (pruebas en las tareas 2 y 9).
4. **Otro administrador cambió el estado o los pesos entre que se cargó la pantalla y se guardó:** 409 con el mensaje del servidor y recarga de los datos vigentes, sin perder lo escrito en la observación (pruebas en las tareas 3, 4, 9 y 10).
5. **Base sin reportes:** Priorización muestra el estado vacío y el mapa sin puntos no falla (pruebas en las tareas 1 y 8).

---

## Grupo A · rama `feat/admin-ranking-api`

### Tarea 1: ranking, resumen y mapa de calor (backend)

**Archivos:**
- Crear: `backend/app/modules/admin/domain/ranking_view.py`, `backend/app/modules/admin/domain/ports.py`, `backend/app/modules/admin/application/read_dashboard.py`, `backend/app/modules/admin/infrastructure/dashboard_reader.py`, `backend/app/modules/admin/presentation/router.py`, `backend/app/modules/admin/presentation/schemas.py`
- Modificar: `backend/app/main.py` (registrar `admin_router` con `API_V1_PREFIX`)
- Pruebas: `backend/tests/unit/test_admin_dashboard.py`, `backend/tests/integration/test_admin_dashboard_api.py`

**Interfaces:**
- Produce (dominio, `ranking_view.py`, todas `@dataclass(frozen=True, slots=True)`):
  - `RankingItem(report_id: UUID, status: ReportStatus, severity: Severity, severity_score: Decimal, flow_score: Decimal, proximity_score: Decimal, urgency_score: Decimal, needs_road_review: bool, address: str, confirmations: int, created_at: datetime)` — cumple el protocolo `Rankable`.
  - `RankingPage(items: Sequence[RankingItem], total: int)`
  - `StatusSummary(active: int, evaluated: int, prioritized: int, repaired: int)`
  - `HeatPoint(lat: float, lon: float, urgency_score: Decimal)`
- Produce (`ports.py`): `class DashboardReader(Protocol)` con `ranking(statuses: frozenset[ReportStatus], limit: int, offset: int) -> RankingPage`, `summary() -> StatusSummary`, `heat_points(bbox: BoundingBox | None, limit: int) -> Sequence[HeatPoint]`. `BoundingBox(min_lon, min_lat, max_lon, max_lat: float)` en el mismo archivo.
- Produce (aplicación): `ReadDashboard(reader: DashboardReader)` con `ranking(statuses: frozenset[ReportStatus] | None, limit: int, offset: int)` (None → activos), `summary()`, `heat_points(bbox, limit=HEATMAP_MAX_POINTS)`; `HEATMAP_MAX_POINTS: Final = 5000`.
- Produce (HTTP):
  - `GET /api/v1/admin/ranking?status=evaluado&status=priorizado&limit=&offset=` → `{"items": [RankingItemResponse], "total": int, "limit": int, "offset": int}`. `RankingItemResponse`: `id, status, severity ("baja"|"media"|"alta"), s, f, p, u` (decimales como número JSON con 2 decimales), `needs_road_review, address, confirmations, created_at`.
  - `GET /api/v1/admin/summary` → `{"active", "evaluated", "prioritized", "repaired"}`.
  - `GET /api/v1/admin/heatmap?bbox=min_lon,min_lat,max_lon,max_lat` → `{"points": [{"lat", "lon", "u"}]}`; bbox mal formado → 422 `INVALID_BBOX`.

- [ ] **Paso 1: pruebas unitarias del caso de uso** con un `DashboardReader` falso: `test_ranking_defaults_to_active_statuses` (pide `{registrado, evaluado, priorizado}`), `test_ranking_rejects_limit_over_100` (lanza `ValueError`), `test_heat_points_capped_at_5000`.
- [ ] **Paso 2: ejecutarlas** — `uv run pytest tests/unit/test_admin_dashboard.py -v` → FALLAN (módulo inexistente).
- [ ] **Paso 3: implementar** dominio, puertos y `ReadDashboard`.
- [ ] **Paso 4: pruebas de integración** contra PostGIS (fixtures de `tests/integration/conftest.py`): 
  - `test_ranking_order_matches_domain_ranking`: crea 6 reportes con empates en U (mismo U, distinta severidad; mismo U y severidad, distintas confirmaciones; todo igual, distinta fecha) y comprueba `ids_api == [r.report_id for r in rank(items)]`.
  - `test_ranking_requires_admin` (ciudadano → 403, sin token → 401).
  - `test_ranking_excludes_repaired_by_default` y `test_ranking_filters_by_status`.
  - `test_ranking_marks_review_road_when_no_road` (`needs_road_review is True`, `address == "Sin vía asociada"`).
  - `test_summary_counts_by_status`: con 2 evaluados, 1 priorizado, 1 reparado → `{"active": 3, "evaluated": 2, "prioritized": 1, "repaired": 1}`.
  - `test_summary_and_ranking_empty_database` (`total == 0`, `items == []`, todos los conteos en 0).
  - `test_heatmap_points_inside_bbox_only` y `test_heatmap_invalid_bbox_is_422`.
- [ ] **Paso 5: implementar `SqlDashboardReader`** en `dashboard_reader.py`: S, F y P de la evaluación más reciente de cada reporte (`DISTINCT ON (id_reporte) … ORDER BY id_reporte, id_evaluacion DESC`, o `LATERAL`), U de `reporte.puntaje_prioridad`, confirmaciones con subconsulta `count(*)`; solo reportes con evaluación; orden de las restricciones globales en SQL. Coordenadas con `ST_Y`/`ST_X`, filtro bbox con `ST_Intersects(ubicacion, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))`. Router y esquemas Pydantic (`ConfigDict(frozen=True)`).
- [ ] **Paso 6: ejecutar** `uv run pytest tests/unit/test_admin_dashboard.py tests/integration/test_admin_dashboard_api.py -v` → PASAN; `uv run ruff check . && uv run ruff format --check . && uv run mypy` limpios.
- [ ] **Paso 7: commit** — `feat(admin): ranking, resumen por estado y mapa de calor` (`Refs: HU-08`).

### Integración del grupo A
- [ ] Suite completa del backend en verde; `git merge --no-ff` a `main`, `git push`, CI en verde, borrar la rama.

---

## Grupo B · rama `feat/admin-report-status-api`

### Tarea 2: detalle del reporte para el administrador (backend)

**Archivos:**
- Crear: `backend/app/modules/admin/domain/report_detail.py`, `backend/app/modules/admin/application/get_admin_report.py`, `backend/app/modules/admin/infrastructure/report_detail_reader.py`
- Modificar: `backend/app/modules/admin/domain/ports.py`, `backend/app/modules/admin/presentation/router.py`, `backend/app/modules/admin/presentation/schemas.py`
- Pruebas: `backend/tests/unit/test_admin_report_detail.py`, `backend/tests/integration/test_admin_report_detail_api.py`

**Interfaces:**
- Produce (dominio): `AdminReportDetail(id, status, allowed_next_statuses: tuple[ReportStatus, ...], severity, description: str | None, location: GeoPoint, address: str, road: RoadInfo | None, reporter_name: str, created_at, confirmations: int, evaluation: EvaluationBreakdown | None, history: Sequence[AdminHistoryEntry])`; `RoadInfo(name: str | None, highway: str)`; `EvaluationBreakdown(severity_score, flow_score, proximity_score, urgency_score: Decimal, w_severity, w_flow, w_proximity: Decimal, config_id: int, service: NearestService | None, calculated_at: datetime)`; `NearestService(name: str | None, service_type: str, distance_m: Decimal)`; `AdminHistoryEntry(previous_status: ReportStatus | None, status: ReportStatus, changed_at: datetime, note: str | None, changed_by_name: str | None)` (None = el sistema). `allowed_next_statuses` sale de `status_machine.allowed_next_statuses` **sin** las transiciones del sistema (`SYSTEM_TRANSITIONS`).
- Produce (puerto): `AdminReportReader.get(report_id: UUID) -> AdminReportDetail | None`; aplicación `GetAdminReport(reader).execute(report_id) -> AdminReportDetail`, lanza `ReportNotFoundError`.
- Produce (HTTP): `GET /api/v1/admin/reports/{id}` → `AdminReportResponse` con los mismos campos en `snake_case` (`location: {"lat","lon"}`, decimales con 2 cifras, `evaluation: null` si no hay); 404 `REPORT_NOT_FOUND`.

- [ ] **Paso 1: pruebas unitarias**: `test_allowed_next_statuses_exclude_system_transition` (desde `registrado` → `()`; desde `evaluado` → `(priorizado, reparado)`; desde `reparado` → `()`), `test_missing_report_raises_not_found`.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar** dominio y caso de uso.
- [ ] **Paso 4: pruebas de integración**: `test_admin_detail_full_breakdown` (S, F, P, U, pesos de la versión usada, servicio y distancia, nombre del reportante, historial con observación y `changed_by_name` del administrador y `null` en la evaluación del sistema), `test_admin_detail_without_road_or_service` (`road is None`, `evaluation.service is None`, `address == "Sin vía asociada"`), `test_admin_detail_without_evaluation` (`evaluation is None`), `test_admin_detail_requires_admin`, `test_admin_detail_unknown_id_is_404`.
- [ ] **Paso 5: implementar `SqlAdminReportReader`**: evaluación más reciente con su `config_evaluacion` (pesos), `servicio_critico` por `id_servicio`, `via` por `id_via`, `usuario.nombre` del autor y de cada entrada del historial (LEFT JOIN), historial por `fecha_cambio` asc.
- [ ] **Paso 6: ejecutar** las pruebas → PASAN; lint y tipos limpios.
- [ ] **Paso 7: commit** — `feat(admin): detalle del reporte con desglose del cálculo` (`Refs: HU-08, HU-12`).

### Tarea 3: cambio de estado con historial (backend)

**Archivos:**
- Crear: `backend/app/modules/admin/application/change_report_status.py`
- Modificar: `backend/app/modules/reports/domain/ports.py` (método `lock_status`), `backend/app/modules/reports/infrastructure/status_history.py` o el repositorio de reportes (implementarlo), `backend/app/modules/admin/presentation/router.py`, `schemas.py`
- Pruebas: `backend/tests/unit/test_change_report_status.py`, `backend/tests/integration/test_admin_status_api.py`

**Interfaces:**
- Consume: `change_status(current, new, *, changed_by, note)` e `InvalidStatusTransitionError` de `status_machine.py`; `StatusHistoryRecorder.apply(report_id, change)`; `TransactionManager`.
- Produce: puerto `ReportStatusLock.lock_status(report_id: UUID) -> ReportStatus | None` (`SELECT estado … FOR UPDATE`); `ChangeReportStatus(lock, recorder, transaction).execute(report_id: UUID, new: ReportStatus, admin_id: UUID, note: str | None) -> StatusChange`; lanza `ReportNotFoundError` o `InvalidStatusTransitionError`; hace `rollback` ante cualquier error.
- Produce (HTTP): `PATCH /api/v1/admin/reports/{id}/status`, cuerpo `{"status": "priorizado", "note": "…"}` (`note` opcional, máximo `NOTE_MAX_LENGTH = 1000` caracteres) → 200 con `AdminReportResponse` actualizado; 404 `REPORT_NOT_FOUND`; 409 `INVALID_STATUS_TRANSITION` con `message` = motivo de la excepción y `details: {"current_status": …}`; 422 si `note` es muy larga.

- [ ] **Paso 1: pruebas unitarias** con dobles: `test_change_records_history_and_commits`, `test_invalid_transition_rolls_back` (de `reparado` a `priorizado`), `test_admin_cannot_do_system_transition` (de `registrado` a `evaluado`), `test_blank_note_saved_as_none`, `test_unknown_report_raises_not_found`.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar** `ChangeReportStatus` y `lock_status`.
- [ ] **Paso 4: pruebas de integración**: `test_patch_status_evaluated_to_prioritized` (200; historial con la observación y el administrador), `test_patch_status_skip_to_repaired` (evaluado → reparado), `test_patch_status_backwards_is_409`, `test_patch_status_stale_is_409` (el reporte ya pasó a reparado por otra petición antes; 409 con `current_status == "reparado"`), `test_patch_status_does_not_change_urgency` (U igual antes y después), `test_patch_status_requires_admin`.
- [ ] **Paso 5: implementar la ruta** y mapear errores.
- [ ] **Paso 6: ejecutar** → PASAN; suite completa del backend en verde.
- [ ] **Paso 7: commit** — `feat(admin): cambiar el estado del reporte con historial` (`Refs: HU-12`).

### Integración del grupo B
- [ ] Igual que el grupo A.

---

## Grupo C · rama `feat/admin-weights-api`

### Tarea 4: pesos vigentes, guardar con 409 y versiones (backend)

**Archivos:**
- Modificar: `backend/app/modules/priority/application/update_weights.py`, `backend/app/modules/priority/domain/ports.py` (`lock_current`), `backend/app/modules/priority/infrastructure/weights_repository.py`, `backend/app/modules/admin/presentation/router.py`, `schemas.py`
- Crear: `backend/app/modules/priority/application/errors.py` (si no existe un lugar mejor)
- Pruebas: `backend/tests/unit/test_priority_application.py` (ampliar), `backend/tests/integration/test_admin_weights_api.py`

**Interfaces:**
- Produce: `WeightVersionRepository.lock_current() -> WeightVersion | None` (`SELECT … WHERE vigente FOR UPDATE`); `UpdateWeights.execute(weights: Weights, admin_id: UUID, base_version_id: int) -> WeightsUpdateResult`, lanza `StaleWeightsVersionError(current_id: int)` si `lock_current().id != base_version_id` (antes de crear la versión, dentro de la transacción, con `rollback`).
- Produce (HTTP):
  - `GET /api/v1/admin/weights` → `WeightVersionResponse {"id", "w_severity", "w_flow", "w_proximity", "created_at", "created_by_name"}` (`created_by_name` null = configuración inicial).
  - `PUT /api/v1/admin/weights`, cuerpo `{"base_version_id": int, "w_severity": "0.50", "w_flow": "0.30", "w_proximity": "0.20"}` (cadenas o números; se convierten a `Decimal` sin pasar por `float`) → 200 `{"version": WeightVersionResponse, "recalculated_reports": int}`; 409 `WEIGHTS_VERSION_CONFLICT` con `details: {"current_version_id"}`; 422 `INVALID_WEIGHTS` con el mensaje de `InvalidWeightsError`.
  - `GET /api/v1/admin/weights/versions?limit=&offset=` → `{"items": [WeightVersionResponse + "is_current"], "limit", "offset"}`, de la más nueva a la más antigua.

- [ ] **Paso 1: pruebas unitarias**: `test_update_weights_with_stale_base_raises_and_rolls_back`, `test_update_weights_with_current_base_creates_version`.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar** `lock_current` y la comprobación en `UpdateWeights`; ajustar los llamadores existentes de `execute`.
- [ ] **Paso 4: pruebas de integración**: `test_get_current_weights`, `test_put_weights_recalculates_active_reports` (reporte activo con U nueva; reporte reparado sin evaluación nueva; `recalculated_reports` correcto), `test_put_weights_sum_not_one_is_422` (`0.50/0.30/0.19`), `test_put_weights_three_decimals_is_422` (`0.505`), `test_put_weights_stale_base_is_409`, `test_versions_newest_first`, `test_weights_routes_require_admin`.
- [ ] **Paso 5: implementar las rutas.**
- [ ] **Paso 6: ejecutar** → PASAN; suite completa en verde. Quitar de `AGENTS.md` (estado) el pendiente «rutas HTTP de pesos y 409».
- [ ] **Paso 7: commit** — `feat(admin): rutas de pesos con versiones y conflicto 409` (`Refs: HU-14`).

### Integración del grupo C
- [ ] Igual que el grupo A.

---

## Grupo D · rama `feat/auth-sesion-web`

### Tarea 5: variante web de la sesión (decisión 42)

**Archivos:**
- Crear: `backend/app/modules/auth/presentation/web_router.py`, `backend/app/modules/auth/presentation/web_session.py` (cookie y CSRF)
- Modificar: `backend/app/modules/auth/application/login.py` (`required_role`), la clase `RefreshSession` (mismo parámetro), `backend/app/modules/auth/application/errors.py` (`InsufficientRoleError`), `backend/app/main.py` (registrar el router; `CORSMiddleware` con `allow_credentials=True` y cabeceras permitidas `Authorization, Content-Type, X-CSRF-Protection`), `docs/adr/0004-autenticacion.md` (flujo web)
- Pruebas: `backend/tests/unit/test_auth_application.py` (ampliar), `backend/tests/integration/test_auth_web_api.py`

**Interfaces:**
- Produce: `Login.execute(email, password, required_role: UserRole | None = None)`; si la contraseña es correcta pero el rol no coincide, lanza `InsufficientRoleError` **sin emitir sesión** y sin contar como intento fallido. `RefreshSession.execute(token, required_role: UserRole | None = None)`, igual.
- Produce (HTTP), todas con `X-CSRF-Protection: 1` obligatoria (si falta → 403 `CSRF_CHECK_FAILED`) y `Origin` en `CORS_ORIGINS` (si no → 403 `CSRF_CHECK_FAILED`):
  - `POST /api/v1/auth/web/login` (mismos límites que `/auth/login`) → 200 `{"access_token", "token_type": "bearer", "expires_in"}` + `Set-Cookie: sr_refresh=…; HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth/web; Max-Age=<REFRESH_TOKEN_TTL_DAYS en s>`; 401 `INVALID_CREDENTIALS`; 403 `ADMIN_ROLE_REQUIRED` («Esta cuenta no tiene acceso al panel.»); 429 igual que el login de la app.
  - `POST /api/v1/auth/web/refresh` (lee la cookie) → 200 como el login y cookie rotada; sin cookie o inválida → 401 `INVALID_SESSION` y cookie borrada.
  - `POST /api/v1/auth/web/logout` → 204, revoca el refresco de la cookie y la borra; repetirlo no da error.
- La variante de la app (`/auth/login`, `/refresh`, `/logout`) no cambia.

- [ ] **Paso 1: pruebas unitarias**: `test_login_with_required_role_rejects_citizen_without_session`, `test_login_role_mismatch_is_not_a_failed_attempt`, `test_refresh_with_required_role_rejects_citizen`.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar** `required_role` e `InsufficientRoleError`.
- [ ] **Paso 4: pruebas de integración** (con `httpx`/`TestClient`, cabecera `Origin` de la lista): `test_web_login_sets_httponly_cookie_and_no_refresh_in_body`, `test_web_login_citizen_is_403`, `test_web_login_without_csrf_header_is_403`, `test_web_login_foreign_origin_is_403`, `test_web_refresh_rotates_cookie`, `test_web_refresh_reused_cookie_revokes_chain` (comportamiento existente de reutilización), `test_web_refresh_without_cookie_is_401_and_clears`, `test_web_logout_revokes_and_clears`, `test_cors_preflight_allows_credentials_for_panel_origin`, `test_app_login_unchanged`.
- [ ] **Paso 5: implementar** `web_router.py` y `web_session.py` (atributos de la cookie como constantes con nombre).
- [ ] **Paso 6: ejecutar** → PASAN; suite completa en verde. Completar el ADR 0004 con el flujo web y marcar en la bitácora la decisión 42 como aplicada en lo que toca a la sesión.
- [ ] **Paso 7: commit** — `feat(auth): sesión web del panel con cookie HttpOnly y CSRF` (`Refs: HU-10, propuesta-42`).

### Integración del grupo D
- [ ] Igual que el grupo A.

---

## Grupo E · rama `feat/admin-web-base`

### Tarea 6: proyecto del panel, tema y CI

**Archivos:**
- Crear: `admin-web/` con `package.json`, `.npmrc` (`save-exact=true`), `vite.config.ts`, `tsconfig.json` (`strict`, `noUncheckedIndexedAccess`), `eslint.config.js`, `.prettierrc`, `index.html` (`lang="es-CO"`, `<meta name="robots" content="noindex">`), `src/main.tsx`, `src/app/App.tsx`, `src/theme/tokens.css`, `src/theme/global.css`, `src/format/format.ts`, `src/components/StatusChip.tsx`, `SeverityChip.tsx`, `ReviewRoadChip.tsx`, `StateViews.tsx` (`LoadingView`, `EmptyView`, `ErrorView` con «Reintentar»), `src/api/schema.d.ts` (generado), `src/config.ts`, `src/test/setup.ts`, `.env.example`
- Modificar: `.github/workflows/ci.yml` (job `admin-web`), `admin-web/README.md`
- Pruebas: `src/format/format.test.ts`, `src/components/chips.test.tsx`

**Interfaces:**
- Produce: `config.apiBaseUrl` (de `VITE_API_BASE_URL`, obligatorio), `config.tileUrl` (de `VITE_TILE_URL`, por defecto `https://tile.openstreetmap.org/{z}/{x}/{y}.png`).
- Produce (`format.ts`): `formatScore(n: number): string` (`8.7 → "8,70"`), `formatShortDate(iso: string): string` (`"2026-10-13T21:05:00Z" → "13 oct"`, zona `America/Bogota`), `formatDateTime(iso: string): string` (`→ "13 oct, 4:05 p. m."`), `formatDistance(m: number): string` (`225.54 → "225,5 m"`), `statusLabel(s: ReportStatus)`, `severityLabel(s)`.
- Produce: tipos `ReportStatus = "registrado" | "evaluado" | "priorizado" | "reparado"` y `Severity = "baja" | "media" | "alta"` exportados desde `src/api/types.ts` (alias sobre `schema.d.ts`).
- Scripts npm: `dev`, `build`, `preview`, `lint`, `format:check`, `typecheck` (`tsc --noEmit`), `test` (`vitest run`), `e2e` (`playwright test`), `gen:api` (`openapi-typescript $VITE_API_BASE_URL/openapi.json -o src/api/schema.d.ts`).
- Tokens (`tokens.css`, variables CSS): exactamente los de la guía 10.1 (tinta `#1B2430`, papel `#F5F3EE`, ámbar `#F5B800`, línea `#E2DED5`, texto secundario `#5B6573`, colores y chips de los cuatro estados, severidades `#2B6CB0`/`#B45F06`/`#B42318`); fuentes **Archivo** 700/800 y **Manrope** 400–700 con `@fontsource/archivo` y `@fontsource/manrope` (sin CDN, por la CSP).

- [ ] **Paso 1: crear el proyecto** con Vite (plantilla `react-ts`), React 18.3.1, y añadir dependencias: `@tanstack/react-query`, `react-router-dom`, `leaflet`, `react-leaflet` (versión compatible con React 18), `leaflet.heat`, `leaflet.markercluster`, `@fontsource/archivo`, `@fontsource/manrope`; desarrollo: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`, `msw`, `@playwright/test`, `openapi-typescript`, `eslint` (+ `typescript-eslint`, `eslint-plugin-react-hooks`, `eslint-plugin-jsx-a11y`), `prettier`. Generar `schema.d.ts` con la API corriendo (grupos A–D integrados).
- [ ] **Paso 2: pruebas** `format.test.ts` (los ejemplos de arriba, más `formatScore(10) → "10,00"`) y `chips.test.tsx` (cada chip muestra su texto: «Evaluado», «Alta», «Revisar vía»; no depende solo del color).
- [ ] **Paso 3: ejecutarlas** — `npm test` → FALLAN.
- [ ] **Paso 4: implementar** `format.ts`, tokens y chips.
- [ ] **Paso 5: ejecutar** `npm run lint && npm run format:check && npm run typecheck && npm test && npm run build` → todo en verde.
- [ ] **Paso 6: CI**: job `admin-web` (Node 22 LTS, `working-directory: admin-web`): `npm ci`, `lint`, `format:check`, `typecheck`, `test`, `npm audit --audit-level=high`, `build`. Añadir `admin-web` a Dependabot (`npm`).
- [ ] **Paso 7: commit** — `chore(admin-web): proyecto React con tema, formato y CI` (`Refs: HU-08`). Registrar en la bitácora las herramientas como aplicadas (decisión 76).

### Tarea 7: cliente de la API, sesión e inicio de sesión

**Archivos:**
- Crear: `src/api/client.ts`, `src/auth/session.ts`, `src/auth/SessionProvider.tsx`, `src/auth/RequireAdmin.tsx`, `src/auth/LoginPage.tsx`, `src/app/router.tsx`, `src/app/Layout.tsx` (navegación lateral: Priorización, Pesos del modelo; nombre del funcionario; «Cerrar sesión»), `src/components/AuthImage.tsx`, `src/test/server.ts` (MSW)
- Pruebas: `src/api/client.test.ts`, `src/auth/LoginPage.test.tsx`, `src/auth/RequireAdmin.test.tsx`, `src/components/AuthImage.test.tsx`

**Interfaces:**
- Produce (`client.ts`): `class ApiError extends Error { status: number; code: string; details: Record<string, unknown> }`; `createApiClient(opts: { baseUrl: string; getAccessToken: () => string | null; refresh: () => Promise<string | null>; onSessionEnded: () => void })` que devuelve `{ get<T>(path, query?), patch<T>(path, body), put<T>(path, body), getBlob(path) }`. Ante un 401 llama a `refresh` **una sola vez aunque haya varias peticiones en curso** (una promesa compartida), reintenta cada petición una vez y, si el refresco devuelve `null`, llama a `onSessionEnded`. Errores de red → `ApiError` con `code = "NETWORK_ERROR"` y mensaje «No hay conexión con el servidor. Revisa tu red e intenta de nuevo.».
- Produce (`session.ts`): `webLogin(email, password): Promise<{ accessToken: string; expiresIn: number }>`, `webRefresh(): Promise<{ accessToken; expiresIn } | null>`, `webLogout(): Promise<void>`; todas con `credentials: "include"` y `X-CSRF-Protection: 1`.
- Produce (`SessionProvider`): contexto `useSession(): { status: "checking" | "signed-in" | "signed-out"; user: { name: string } | null; signIn(email, password); signOut(); api }`. Al montar intenta `webRefresh()` (recupera la sesión tras recargar). Programa un refresco al 80 % de `expiresIn`. El nombre sale de `GET /api/v1/me`.
- Produce: `<RequireAdmin>` (rutas protegidas; `checking` → `LoadingView`; `signed-out` → `/ingresar`); `<AuthImage src alt />` (pide con `getBlob`, muestra `URL.createObjectURL`, lo revoca al desmontar).
- Rutas: `/ingresar`, `/` → `/priorizacion`, `/priorizacion`, `/reportes/:id`, `/pesos`.
- Textos de `LoginPage` según el Figma («inicio de sesión de funcionarios»); errores: 401 → «Correo o contraseña incorrectos.», 403 `ADMIN_ROLE_REQUIRED` → «Esta cuenta no tiene acceso al panel.», 429 → mensaje con los minutos de `Retry-After`.

- [ ] **Paso 1: pruebas**: `client.test.ts` → `single_refresh_for_concurrent_401s` (3 peticiones con 401, `refresh` llamado 1 vez, las 3 resuelven), `session_ended_when_refresh_fails` (`onSessionEnded` llamado, se lanza `ApiError` 401), `network_error_message`; `LoginPage.test.tsx` → `shows_admin_role_required_message`, `shows_lockout_minutes`, `disables_submit_while_sending`; `RequireAdmin.test.tsx` → `redirects_to_login_when_signed_out`, `restores_session_after_reload` (MSW responde al refresco web con un token); `AuthImage.test.tsx` → `revokes_object_url_on_unmount`.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar.**
- [ ] **Paso 4: ejecutar** `npm run lint && npm run typecheck && npm test` → en verde.
- [ ] **Paso 5: commit** — `feat(admin-web): sesión del funcionario e inicio de sesión` (`Refs: HU-10`).

### Integración del grupo E
- [ ] Lint, tipos y pruebas del panel en verde; *merge* a `main`, CI en verde, borrar la rama.

---

## Grupo F · rama `feat/admin-web-priorizacion`

### Tarea 8: pantalla Priorización

**Archivos:**
- Crear: `src/features/prioritization/api.ts`, `PrioritizationPage.tsx`, `SummaryCards.tsx`, `HeatMap.tsx`, `RankingTable.tsx`, `src/components/MapAttribution.tsx` (si `react-leaflet` no la muestra con el texto requerido), `src/types/leaflet-plugins.d.ts`
- Pruebas: `PrioritizationPage.test.tsx`, `RankingTable.test.tsx`

**Interfaces:**
- Consume: `GET /admin/summary`, `GET /admin/ranking`, `GET /admin/heatmap` (tarea 1); `useSession().api`; chips y formatos (tarea 6).
- Produce (`api.ts`): hooks `useSummary()`, `useRanking({ statuses, page })` (20 por página), `useHeatPoints()`, con claves de consulta `["admin", "summary"]`, `["admin", "ranking", statuses, page]`, `["admin", "heatmap"]` (tareas 9 y 10 las invalidan).
- Pantalla según el Figma «Priorización» y «Panel · Priorización · Estados»: tarjetas Activos · Evaluados · Priorizados · Reparados; mapa centrado en Pasto (centro del `REPORT_AREA_BBOX`, zoom 14) con capa de calor (`leaflet.heat`, intensidad = U/10) y **leyenda con números** (0–10); capa opcional «Ver reportes» con marcadores agrupados (`leaflet.markercluster`); tabla con posición, dirección, chips de severidad y estado, S, F, P, U con coma, confirmaciones, fecha corta y chip «Revisar vía»; filtro por estado (por defecto activos); paginación; cada fila navega a `/reportes/:id` (también con teclado).

- [ ] **Paso 1: pruebas**: `renders_ranking_with_comma_decimals` (fila con `u: 8.7` muestra `8,70`), `shows_review_road_chip`, `row_click_and_enter_navigate_to_detail`, `empty_state_when_no_reports` (texto del estado vacío del Figma y mapa sin error), `error_state_with_retry` (500 → «Reintentar» vuelve a pedir), `status_filter_requests_selected_statuses`, `pagination_requests_next_offset`, `heatmap_legend_shows_numbers`. Leaflet con jsdom: simular `HeatMap` en las pruebas de la página y probar solo su leyenda.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar.**
- [ ] **Paso 4: ejecutar** lint, tipos y pruebas → en verde; comprobar a mano en `npm run dev` contra la API local que el mapa carga y se ve la atribución.
- [ ] **Paso 5: commit** — `feat(admin-web): pantalla de priorización con mapa de calor` (`Refs: HU-08`).

### Integración del grupo F
- [ ] Igual que el grupo E.

---

## Grupo G · rama `feat/admin-web-detalle`

### Tarea 9: pantalla Detalle y estado

**Archivos:**
- Crear: `src/features/report-detail/api.ts`, `ReportDetailPage.tsx`, `ScoreBreakdown.tsx`, `StatusChangeForm.tsx`, `HistoryList.tsx`, `LocationMap.tsx`
- Pruebas: `ReportDetailPage.test.tsx`, `StatusChangeForm.test.tsx`

**Interfaces:**
- Consume: `GET /admin/reports/{id}` (tarea 2), `PATCH /admin/reports/{id}/status` (tarea 3), fotos `/reports/{id}/photo` con `AuthImage` (tarea 7).
- Produce: `useAdminReport(id)` (clave `["admin", "report", id]`), `useChangeStatus(id)` que al terminar invalida `["admin", "report", id]`, `["admin", "ranking"]`, `["admin", "summary"]` y `["admin", "heatmap"]`.
- Pantalla según el Figma «Detalle y estado»: foto, mapa con el punto (atribución OSM), vía (`name` + `highway`) o «Sin vía asociada» con chip «Revisar vía», reportante, fecha, descripción, confirmaciones; desglose: S, F, P con su peso y U = w₁·S + w₂·F + w₃·P **tal como lo da la API** (sin recalcular), versión de pesos, servicio crítico y distancia o «Ningún servicio crítico a menos de 500 m», o «Pendiente de evaluación» si `evaluation` es `null`; formulario de cambio de estado con las opciones de `allowed_next_statuses` (si está vacío: «Este reporte no admite más cambios de estado.») y observación (máx. 1000, contador); historial con fecha y hora, transición, observación y quién («Sistema» si `changed_by_name` es `null`).

- [ ] **Paso 1: pruebas**: `shows_breakdown_from_api` (valores con coma, sin cálculo en el cliente), `shows_no_road_and_no_service_texts`, `shows_pending_evaluation`, `status_options_come_from_api`, `final_status_shows_no_more_changes`, `submit_disabled_while_sending`, `conflict_409_shows_message_reloads_and_keeps_note` (la observación sigue escrita), `history_shows_system_for_null_author`, `photo_uses_auth_image`.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar.**
- [ ] **Paso 4: ejecutar** → en verde; comprobación manual del cambio de estado contra la API local.
- [ ] **Paso 5: commit** — `feat(admin-web): detalle del reporte y cambio de estado` (`Refs: HU-12`).

### Integración del grupo G
- [ ] Igual que el grupo E.

---

## Grupo H · rama `feat/admin-web-pesos`

### Tarea 10: pantalla Pesos del modelo

**Archivos:**
- Crear: `src/features/weights/api.ts`, `WeightsPage.tsx`, `WeightsForm.tsx`, `NormalizationRules.tsx`, `VersionsList.tsx`, `src/features/weights/parseWeight.ts`
- Pruebas: `parseWeight.test.ts`, `WeightsForm.test.tsx`, `WeightsPage.test.tsx`

**Interfaces:**
- Consume: rutas de la tarea 4.
- Produce: `parseWeight(text: string): string | null` → normaliza a cadena con punto y 2 decimales (`"0,5" → "0.50"`, `"0.30" → "0.30"`, `"1" → "1.00"`; `"0,505"`, `"-0.1"`, `"1.01"`, `"abc"` → `null`). La suma se comprueba con enteros en centésimas (nunca con `float`).
- Produce: `useCurrentWeights()`, `useWeightVersions(page)`, `useSaveWeights()` que envía `base_version_id` y al terminar invalida `["admin", "weights"]`, `["admin", "ranking"]`, `["admin", "summary"]`, `["admin", "heatmap"]` y `["admin", "report"]`.
- Pantalla según el Figma «Pesos del modelo»: tres controles (deslizador de 0,00 a 1,00, paso 0,01, más campo numérico con coma) para w₁ (severidad), w₂ (flujo) y w₃ (proximidad); total en vivo «Σ = 1,00» y mensaje si no suma; reglas de normalización en solo lectura (texto de la guía 2.2: S baja 3, media 6, alta 10; F primary 10, secondary 7, tertiary 5, residential/unclassified/service 2, sin vía 2; P 10 hasta 100 m, lineal hasta 0 a 500 m); «Guardar y recalcular» con confirmación que dice cuántos reportes se recalcularon; lista de versiones (fecha, autor o «Configuración inicial», pesos, vigente).

- [ ] **Paso 1: pruebas**: `parseWeight.test.ts` (los casos de arriba); `WeightsForm.test.tsx` → `save_disabled_when_sum_not_one` (0,50 + 0,30 + 0,19), `accepts_comma_decimals`, `rejects_three_decimals_with_message`; `WeightsPage.test.tsx` → `save_sends_base_version_and_shows_recalculated_count`, `conflict_409_offers_reload_current_version`, `server_422_message_shown`, `versions_list_marks_current`.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar.**
- [ ] **Paso 4: ejecutar** → en verde; comprobación manual: guardar pesos y ver el ranking recalculado.
- [ ] **Paso 5: commit** — `feat(admin-web): pesos del modelo con versiones` (`Refs: HU-14`).

### Integración del grupo H
- [ ] Igual que el grupo E.

---

## Grupo I · rama `feat/demo-seed`

### Tarea 11: datos de demostración

**Archivos:**
- Crear: `backend/app/modules/admin/application/demo_seed.py`, `backend/app/modules/admin/infrastructure/demo_points.py`, `backend/app/demo/photos/` (4–6 JPEG genéricos de pavimento con licencia libre o propios del responsable, sin EXIF, con `README.md` de origen y licencia)
- Modificar: `backend/app/cli.py` (subcomando `seed-demo` con `--remove`)
- Pruebas: `backend/tests/unit/test_demo_seed.py`, `backend/tests/integration/test_demo_seed.py`, `backend/tests/unit/test_cli.py` (ampliar)

**Interfaces:**
- Produce: constantes `DEMO_EMAIL_DOMAIN: Final = "demo.invalid"`, `DEMO_CITIZEN_EMAIL = "ciudadano@demo.invalid"`, `DEMO_ADMIN_EMAIL = "funcionario@demo.invalid"` (contraseña aleatoria no usable: no se puede iniciar sesión con ella), `DEMO_REPORT_COUNT: Final = 32`.
- Produce: `DemoPointPicker.pick() -> Sequence[DemoPoint]` (`DemoPoint(location: GeoPoint, severity: Severity)`), determinista con los mismos datos OSM: 8 puntos en vías `primary`, 8 en `secondary`, 6 en `tertiary`, 6 en `residential` (punto medio de la vía con `ST_LineInterpolatePoint`, vías ordenadas por `id_via`, sin repetir vía y a más de 25 m de los demás puntos), 2 a menos de 100 m de un servicio crítico, 2 a más de 30 m de toda vía (dentro de `REPORT_AREA_BBOX`); severidades en ciclo baja → media → alta.
- Produce: `SeedDemo.execute() -> int` (reportes creados): crea los dos usuarios, cada reporte con su foto (procesada con el `PhotoProcessor` existente), su historial inicial y **la evaluación del motor real** (`ReportEvaluator`), y luego mueve 8 a `priorizado` y 4 a `reparado` con `change_status` firmados por el funcionario de demostración, con observaciones de demostración. Si ya existen datos de demostración, no hace nada y lo dice. `SeedDemo.remove() -> int`: borra los reportes de los usuarios `@demo.invalid` (evidencias, historial, evaluaciones y confirmaciones incluidos), sus fotos del almacenamiento y los usuarios.
- CLI: `python -m app.cli seed-demo` imprime «Datos de demostración: N reportes creados. No son datos de campo.»; `seed-demo --remove` imprime los borrados.

- [ ] **Paso 1: pruebas unitarias**: `test_seed_is_idempotent` (segunda ejecución no crea nada), `test_seed_uses_engine_evaluation` (el doble del evaluador se llama una vez por reporte), `test_cli_seed_demo_dispatch`.
- [ ] **Paso 2: ejecutarlas** → FALLAN.
- [ ] **Paso 3: implementar.**
- [ ] **Paso 4: pruebas de integración** (con datos OSM de prueba de `test_osm_import.py`/`conftest`): `test_seed_creates_reports_with_all_cases` (hay reportes de las tres severidades, de cada jerarquía, al menos uno con `needs_road_review`, al menos uno con P = 10, estados priorizado y reparado con historial), `test_seed_remove_deletes_everything` (0 filas de los usuarios demo y 0 archivos de sus fotos), `test_demo_admin_cannot_log_in`.
- [ ] **Paso 5: ejecutar** → PASAN; suite completa en verde.
- [ ] **Paso 6: commit** — `feat(admin): datos de demostración marcados para el panel` (`Refs: HU-08`).

### Integración del grupo I
- [ ] Igual que el grupo A.

---

## Grupo J · rama `chore/admin-web-compose`

### Tarea 12: servir el panel con Docker Compose, pruebas de punta a punta y documentación

**Archivos:**
- Crear: `infra/docker/admin-web.Dockerfile` (etapa Node que ejecuta `npm ci && npm run build` con `VITE_API_BASE_URL` y `VITE_TILE_URL` como argumentos; etapa final `nginxinc/nginx-unprivileged` con versión fija, puerto 8080, sin root, `HEALTHCHECK`), `infra/docker/admin-web.nginx.conf`, `admin-web/playwright.config.ts`, `admin-web/e2e/panel.spec.ts`
- Modificar: `infra/docker-compose.yml` (servicio `admin-web`, `127.0.0.1:${ADMIN_WEB_PORT:-8080}:8080`, `depends_on: api`), `.env.example` (`ADMIN_WEB_PORT=8080`, `CORS_ORIGINS=http://localhost:8080,http://localhost:5173`, `ADMIN_API_BASE_URL=http://localhost:8000`), `.github/workflows/ci.yml` (construir la imagen `admin-web` en el job `docker`), `README.md` de la raíz, `admin-web/README.md`

**Interfaces:**
- nginx: SPA con `try_files $uri /index.html`; cabeceras `Content-Security-Policy` (`default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data: <origen de los tiles>; font-src 'self'; connect-src 'self' <API>; frame-ancestors 'none'; base-uri 'none'`), `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex`; caché larga solo para `/assets/`.
- Playwright (local, contra el *stack* de compose con `seed-demo` cargado y un administrador creado; credenciales por `E2E_ADMIN_EMAIL`/`E2E_ADMIN_PASSWORD`; no corre en la CI porque necesita la base con OSM): `login_and_see_ranking`, `change_status_appears_in_history`, `save_weights_creates_version`.

- [ ] **Paso 1: Dockerfile, nginx y compose**; `docker compose -f infra/docker-compose.yml --env-file .env up -d --build` → `admin-web` sano y `http://localhost:8080` muestra el inicio de sesión; las cabeceras se ven con `curl -I`.
- [ ] **Paso 2: recorrido manual** con el *stack*: `create-admin`, `seed-demo`, ingresar, ver ranking y mapa, cambiar un estado, guardar pesos, recargar la página (la sesión se recupera), cerrar sesión.
- [ ] **Paso 3: escribir** `e2e/panel.spec.ts` con los tres flujos y **ejecutarlo**: `npm run e2e` → 3 pasan.
- [ ] **Paso 4: documentar** en el README de la raíz: arranque con el panel, `create-admin`, `seed-demo` (y `--remove`), URL del panel, cómo correr las pruebas del panel y las E2E; aviso de que los datos de demostración no son datos de campo.
- [ ] **Paso 5: commit** — `chore(infra): servir el panel con nginx en Docker Compose` (`Refs: HU-08, HU-17`).

### Integración del grupo J
- [ ] Igual que el grupo A.

---

## Cierre de la fase 6

### Tarea 13: cierre

- [ ] Suite completa (backend y panel) en verde en local y en la CI de `main`; anotar los números de pruebas y la cobertura del backend.
- [ ] `CHANGELOG.md`: mover «Sin publicar» a `0.6.0` con lo de los grupos A–J (y lo pendiente de antes de `v0.5.0`).
- [ ] `AGENTS.md`: fase 6 cerrada en el estado y bloque «Fase 6» como los de las fases 4 y 5.
- [ ] Bitácora: decisión 76 aplicada; propuesta 75 aplicada; nota de que las capturas para la tesis usan datos de demostración. `docs/ajustes-tesis.md`: fila para la sección 4.3 (resultado del objetivo 3 con el panel) y para el cambio de indicadores frente a la maqueta descrita en la tesis.
- [ ] Figma: ajustar el encabezado de Priorización a Activos · Evaluados · Priorizados · Reparados (pedir confirmación al responsable antes de editar el archivo).
- [ ] Versión `0.6.0` en `backend/pyproject.toml` y `admin-web/package.json`; etiqueta anotada `v0.6.0`; `git push origin v0.6.0`.
- [ ] Informar al responsable: qué se construyó, cuántas pruebas pasaron, qué quedó pendiente y propuestas.
