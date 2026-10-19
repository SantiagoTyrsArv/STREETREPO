# Backend para el flujo crítico de la app — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir al backend lo que la app ciudadana necesita y aún no existe: `is_mine` en los posibles duplicados, confirmar un reporte (HU-16, propuesta 48), «mis reportes» (creados y confirmados) y el detalle de un reporte.

**Architecture:** Monolito modular por capas (guía 4.2). Cada endpoint es un caso de uso en `application/` que depende de puertos (`Protocol`) del `domain/`; la infraestructura los implementa con SQL parametrizado sobre PostGIS; el router traduce errores del dominio a `AppError`. Sin migraciones: las tablas `confirmacion` e `historial_estado` ya existen.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2, PostgreSQL + PostGIS, pytest, uv, ruff, mypy estricto.

**Spec:** `docs/superpowers/specs/2026-10-19-app-flutter-flujo-critico-design.md` (secciones 4.1–4.3 y 7). El plan de la app Flutter es otro documento y depende de este.

## Global Constraints

- Ruta base `/api/v1`; errores con `AppError(code, mensaje en español, status, details)`.
- Consultas parametrizadas siempre; sin `SELECT *`; paginación con tope (`limit` por defecto 20, máximo 50).
- Las confirmaciones **no cambian U** ni el estado del reporte.
- Reportes ajenos: nunca autor, descripción ni ubicación exacta; ubicación pública = `ST_SnapToGrid(ubicacion, PUBLIC_GRID_DEGREES)` (4 decimales).
- Sin permiso de ver → **404**, nunca 403 (no revelar que existe; mismo criterio que la foto).
- Activo = todo estado salvo `reparado`.
- Pruebas de integración con `POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 POSTGRES_DB=streetrepo_test uv run pytest` (Docker Desktop encendido y `docker compose -f infra/docker-compose.yml up -d db`); puntos de prueba en el Pacífico (`LON, LAT = -80.0, 0.0`) como las pruebas existentes.
- Antes de cada commit: `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` desde `backend/`.
- Una rama por tarea (guía 8.4), `merge --no-ff` (o `--ff-only` si es un commit) a `main`, sin PR; commits Conventional con `Refs:` y el pie `Co-Authored-By`/`Claude-Session` vigente.

## Review Focus

1. Confirmar dos veces seguidas muy rápido (doble toque) → la segunda responde 409 `CONFIRMATION_ALREADY_EXISTS`, nunca 500 (la carrera la resuelve la restricción única, no un `SELECT` previo). Prueba en Task 2.
2. Un identificador que no es UUID en `/reports/{id}` o `/confirmations` → 422 de validación, no 500. Prueba en Task 4.
3. Tras una supresión de datos (usuario anonimizado), sus confirmaciones desaparecen por `ON DELETE CASCADE` solo si se borra la fila; con anonimización la fila sigue: el conteo no debe romperse y «mis reportes» del usuario anonimizado no se consulta. Prueba en Task 3 (el reporte confirmado por un usuario luego suprimido sigue contando 1 y se lista sin datos del confirmante).
4. `offset` mayor que el total → `items: []` con `total` correcto, no error. Prueba en Task 3.
5. Quien confirmó y además es el autor no existe (propuesta 48), pero un **administrador** que confirmó ve la vista completa: el rol manda sobre la relación. Prueba en Task 4.

---

### Task 1: `is_mine` en los posibles duplicados (propuesta 48, parte A)

**Files:**
- Modify: `backend/app/modules/reports/domain/duplicates.py` (campo `is_mine: bool` en `DuplicateCandidate`)
- Modify: `backend/app/modules/reports/domain/ports.py` (`NearbyReportFinder.find_active_within`)
- Modify: `backend/app/modules/reports/infrastructure/nearby.py` (SQL: `(r.id_usuario = :viewer) AS es_mio`)
- Modify: `backend/app/modules/reports/application/find_nearby.py`, `backend/app/modules/reports/application/create_report.py` (pasan el usuario)
- Modify: `backend/app/modules/reports/presentation/schemas.py` (`DuplicateCandidateResponse.is_mine: bool`; ajustar el docstring «Reporte ajeno» → «Reporte cercano»)
- Test: `backend/tests/integration/test_reports_api.py`, `backend/tests/unit/test_create_report.py` (dobles)

**Interfaces:**
- Produces: `NearbyReportFinder.find_active_within(self, point: GeoPoint, radius_m: float, limit: int, viewer_id: uuid.UUID) -> Sequence[DuplicateCandidate]`; `DuplicateCandidate.is_mine: bool`; JSON `items[].is_mine` en `GET /reports/nearby` y en `details.items[]` del 409 `REPORT_DUPLICATE_NEARBY`.

- [ ] **Step 1: Escribir la prueba que falla** en `test_reports_api.py`:

```python
def test_nearby_marks_the_viewers_own_reports(api: TestClient, conn: Connection) -> None:
    token = _citizen_token(api, "autor@example.test")
    author_id = conn.execute(text("SELECT id_usuario FROM usuario WHERE correo = 'autor@example.test'")).scalar_one()
    own = insert_report(conn, author_id, LON, LAT)
    other = insert_report(conn, insert_user(conn, "otro@example.test"), LON, LAT + 0.0001)
    body = api.get(f"{REPORTS}/nearby", params={"longitude": LON, "latitude": LAT}, headers=bearer(token)).json()
    mine = {item["id"]: item["is_mine"] for item in body["items"]}
    assert mine == {str(own): True, str(other): False}
```

Y en el 409: `test_report_next_to_an_active_one_answers_409_and_saves_nothing` gana `assert response.json()["details"]["items"][0]["is_mine"] is False`. (Ajustar el nombre de la columna de correo si en `usuario` no es `correo`; ver `tests/integration/conftest.py::insert_user`.)

- [ ] **Step 2: Ejecutar y ver que falla** — `uv run pytest tests/integration/test_reports_api.py -k "own_reports or 409" -v` → FAIL (`KeyError: 'is_mine'`).
- [ ] **Step 3: Implementar.** Añadir `:viewer` a `_ACTIVE_WITHIN` (selecciona `r.id_usuario = :viewer AS es_mio` en `cercanos` y lo propaga); `FindPossibleDuplicates.execute` y `CreateReport` pasan `user_id`. Actualizar los dobles de `NearbyReportFinder` en las pruebas unitarias a la firma nueva.
- [ ] **Step 4: Ejecutar** la suite completa del backend (comando de Global Constraints) → PASS, ruff y mypy limpios.
- [ ] **Step 5: Commit** en `improve/propuesta-48-is-mine-duplicados`: `feat(reports): marcar los reportes propios en los posibles duplicados` con `Refs: HU-15, propuesta-48`. Integrar a `main`.

---

### Task 2: Confirmar un reporte (B1, HU-16, propuesta 48 parte B)

**Files:**
- Create: `backend/app/modules/confirmations/domain/errors.py`, `backend/app/modules/confirmations/domain/ports.py`
- Create: `backend/app/modules/confirmations/application/confirm_report.py`
- Create: `backend/app/modules/confirmations/infrastructure/repository.py`
- Create: `backend/app/modules/confirmations/presentation/router.py`, `.../presentation/schemas.py`, `.../presentation/dependencies.py`
- Modify: `backend/app/main.py` (incluir el router con `API_V1_PREFIX`)
- Test: `backend/tests/unit/test_confirm_report.py`, `backend/tests/integration/test_confirmations_api.py`

**Interfaces:**
- Produces (dominio):
  - `ConfirmationTarget(owner_id: uuid.UUID, status: ReportStatus)` (dataclass congelada)
  - errores `ReportNotFoundError`, `ReportNotActiveError`, `OwnReportConfirmationError`, `AlreadyConfirmedError`
  - puerto `ConfirmationRepository` con `find_target(report_id) -> ConfirmationTarget | None`, `add(report_id, user_id) -> None` (lanza `AlreadyConfirmedError` al violar `uq_confirmacion_reporte_usuario`), `count(report_id) -> int`
- Produces (aplicación): `ConfirmReport(confirmations: ConfirmationRepository, rate_limiter: RateLimiter, limit_per_user: RateLimit, clock: Clock, transaction: TransactionManager)` con `execute(report_id: uuid.UUID, user_id: uuid.UUID) -> int` (total tras confirmar). Orden: cupo (`f"confirm:user:{user_id}"`) → objetivo (404) → activo (409) → propio (409) → `add` → `commit` → `count`. Ante cualquier error tras escribir, `rollback`.
- Produces (HTTP): `POST /api/v1/reports/{report_id}/confirmations` → 201 `{"report_id": uuid, "confirmations": int}`; 404 `REPORT_NOT_FOUND`; 409 `REPORT_NOT_ACTIVE`, `CONFIRMATION_OWN_REPORT`, `CONFIRMATION_ALREADY_EXISTS`; 429 `CONFIRMATION_RATE_LIMITED` con `Retry-After`. Cupo = `settings.reports_per_user_per_hour` por hora (mismo valor que `nearby`, cuenta aparte).
- Mensajes: «No encontramos ese reporte.» · «Este reporte ya fue reparado; no necesita más confirmaciones.» · «No puedes confirmar tu propio reporte.» · «Ya confirmaste este reporte.» · «Hiciste muchas confirmaciones en poco tiempo. Intenta de nuevo más tarde.»

- [ ] **Step 1: Pruebas unitarias que fallan** (`test_confirm_report.py`, con un doble en memoria de `ConfirmationRepository` e `InMemoryRateLimiter`):
  - `test_confirming_returns_the_new_total` → `execute(...) == 1` y `commit` llamado una vez.
  - `test_unknown_report_raises_not_found` → `ReportNotFoundError`, nada guardado.
  - `test_repaired_report_cannot_be_confirmed` → `ReportNotActiveError`.
  - `test_author_cannot_confirm_own_report` → `OwnReportConfirmationError`.
  - `test_second_confirmation_raises_already_confirmed_and_rolls_back` → `AlreadyConfirmedError`, `rollback` llamado.
  - `test_rate_limit_applies_per_user` → con `RateLimit(max_requests=2, window=timedelta(hours=1))`, la tercera lanza `RateLimitExceededError`.
- [ ] **Step 2:** `uv run pytest tests/unit/test_confirm_report.py -v` → FAIL (módulo no existe).
- [ ] **Step 3: Implementar** dominio, caso de uso y `SqlConfirmationRepository` (`find_target` lee `reporte.id_usuario` y `estado`; `add` hace `INSERT` y traduce `IntegrityError` con el nombre de la restricción, como `SqlReportRepository._violated_constraint`).
- [ ] **Step 4:** pruebas unitarias → PASS.
- [ ] **Step 5: Pruebas de integración que fallan** (`test_confirmations_api.py`, PostGIS real):
  - `test_a_citizen_confirms_another_citizens_report` → 201, `confirmations == 1`, una fila en `confirmacion`, `puntaje_prioridad` del reporte sin cambios.
  - `test_double_tap_answers_409_not_500` → dos `POST` seguidos: 201 y luego 409 `CONFIRMATION_ALREADY_EXISTS`.
  - `test_author_gets_409_own_report`, `test_repaired_report_gets_409_not_active`, `test_unknown_report_gets_404`.
  - `test_confirmation_without_token_is_401`.
- [ ] **Step 6:** router, esquemas y dependencias; incluir en `main.py`. Ejecutar la suite completa → PASS.
- [ ] **Step 7: Commit** en `feat/confirmations-confirmar-reporte`: `feat(confirmations): confirmar un reporte existente` con `Refs: HU-16, propuesta-48`. Marcar la propuesta 48 como **Aplicada** en `docs/bitacora.md` (commit `docs:` aparte en la misma rama). Integrar.

---

### Task 3: Mis reportes, creados y confirmados (B2)

**Files:**
- Create: `backend/app/modules/reports/domain/my_reports.py`
- Modify: `backend/app/modules/reports/domain/ports.py` (puerto `MyReportsReader`)
- Create: `backend/app/modules/reports/application/list_my_reports.py`
- Create: `backend/app/modules/reports/infrastructure/my_reports.py`
- Create: `backend/app/modules/reports/presentation/me_router.py` (`APIRouter(prefix="/me/reports", tags=["mis reportes"])`)
- Modify: `backend/app/modules/reports/presentation/schemas.py`, `.../dependencies.py`, `backend/app/main.py`
- Test: `backend/tests/unit/test_list_my_reports.py`, `backend/tests/integration/test_my_reports_api.py`

**Interfaces:**
- Produces (dominio, `my_reports.py`):
  - `MAX_PAGE_SIZE: Final = 50`, `DEFAULT_PAGE_SIZE: Final = 20`
  - `OwnReport(details: ReportDetails, confirmations: int)`; `related_at` = `details.created_at`
  - `ConfirmedReport(public: PublicReportView, confirmed_at: datetime)`
  - `PublicReportView(id, location: GeoPoint (pública), status, severity, confirmations: int, road_id, road_name, created_at)` con la propiedad `address` (reusar `display_address`). `DuplicateCandidate` no se toca.
  - `MyReportsPage(items: Sequence[OwnReport | ConfirmedReport], total: int, limit: int, offset: int)`
- Produces: `MyReportsReader.list_for_user(user_id: uuid.UUID, limit: int, offset: int) -> MyReportsPage`; `ListMyReports(reader).execute(user_id, limit, offset) -> MyReportsPage` (valida `1 ≤ limit ≤ MAX_PAGE_SIZE`, `offset ≥ 0`; la validación HTTP también la hace `Query(ge=1, le=50)`).
- Produces (HTTP): `GET /api/v1/me/reports?limit=20&offset=0` → `{"items": [...], "total", "limit", "offset"}`. Elemento `own`: campos de `ReportResponse` + `"relation": "own"`, `"confirmations"`. Elemento `confirmed`: `"relation": "confirmed"`, `id`, `location` (pública), `status`, `severity`, `address`, `confirmations`, `created_at`, `confirmed_at`. Esquemas Pydantic con `relation: Literal["own"]` / `Literal["confirmed"]` en una unión discriminada.
- SQL: `UNION ALL` de los reportes del usuario (fecha = `fecha_creacion`) y sus confirmaciones (fecha = `confirmacion.fecha`), `ORDER BY fecha DESC, id_reporte`, `LIMIT/OFFSET`; `total` con `count(*)` de la misma unión. Conteo de confirmaciones por subconsulta, como en `nearby`.

- [ ] **Step 1: Pruebas unitarias que fallan:** `test_page_size_is_capped` (limit 51 → `ValueError`), `test_negative_offset_is_rejected`, `test_reader_receives_the_user_and_page`.
- [ ] **Step 2:** FAIL → **Step 3:** implementar dominio y caso de uso → **Step 4:** PASS.
- [ ] **Step 5: Pruebas de integración que fallan** (`test_my_reports_api.py`):
  - `test_lists_own_and_confirmed_reports_newest_first` → crea uno propio y confirma uno ajeno después; `[i["relation"] for i in items] == ["confirmed", "own"]`.
  - `test_confirmed_items_hide_exact_location_author_and_description` → la ubicación del confirmado está redondeada a 4 decimales; no hay claves `description`, `priority_score` ni `user_id`.
  - `test_other_citizens_reports_are_not_listed`.
  - `test_offset_past_the_end_returns_empty_items_with_total` → `offset=10` con 2 elementos → `items == []`, `total == 2`.
  - `test_limit_above_50_is_422`.
  - `test_confirmation_by_a_deleted_user_still_counts` (Review Focus 3): el confirmante pide la supresión (`POST /me/data-deletion-requests`); el autor sigue viendo `confirmations == 1`.
- [ ] **Step 6:** infraestructura, router y registro → suite completa PASS.
- [ ] **Step 7: Commit** en `feat/reports-mis-reportes`: `feat(reports): listar mis reportes creados y confirmados` con `Refs: HU-07, HU-16`. Integrar.

---

### Task 4: Detalle de un reporte (B3)

**Files:**
- Create: `backend/app/modules/reports/domain/report_view.py`
- Modify: `backend/app/modules/reports/domain/ports.py` (puerto `ReportViewReader`)
- Create: `backend/app/modules/reports/application/get_report.py`
- Create: `backend/app/modules/reports/infrastructure/report_view.py`
- Modify: `backend/app/modules/reports/presentation/router.py` (`GET /{report_id}`), `schemas.py`, `dependencies.py`
- Test: `backend/tests/unit/test_get_report.py`, `backend/tests/integration/test_report_detail_api.py`

**Interfaces:**
- Consumes: `ReportDetails`, `PublicReportView` (Task 3), `PhotoViewer` (de `get_photo.py`: `user_id`, `is_admin`).
- Produces (dominio):
  - `StatusHistoryEntry(status: ReportStatus, changed_at: datetime, note: str | None)`
  - `FullReportView(details: ReportDetails, confirmations: int, history: Sequence[StatusHistoryEntry])`
  - `LimitedReportView(public: PublicReportView, confirmed_at: datetime, history: Sequence[StatusHistoryEntry])` — historial con `note=None` siempre.
  - `ReportNotVisibleError` (cubre «no existe» y «no puedes verlo»).
- Produces: `ReportViewReader` con `get_details(report_id) -> ReportDetails | None`, `public_view(report_id) -> PublicReportView | None`, `confirmed_at(report_id, user_id) -> datetime | None`, `confirmations(report_id) -> int`, `history(report_id) -> Sequence[StatusHistoryEntry]` (orden `fecha_cambio, id_historial` ascendente, todas las filas, también las de `id_usuario` NULL).
- Produces: `GetReport(reader).execute(report_id, viewer: PhotoViewer) -> FullReportView | LimitedReportView`. Regla: autor o administrador → completa (el rol manda, Review Focus 5); si no, quien confirmó → limitada; si no → `ReportNotVisibleError`.
- Produces (HTTP): `GET /api/v1/reports/{report_id}` → 200 con `relation: "own"` (campos de `ReportResponse` + `confirmations` + `history`) o `relation: "confirmed"` (campos del confirmado de Task 3 + `history`); 404 `REPORT_NOT_FOUND` «No encontramos ese reporte.». Para un administrador que no es autor, `relation` = `"own"` también (vista completa); documentarlo en el docstring.

- [ ] **Step 1: Pruebas unitarias que fallan:** `test_author_gets_the_full_view`, `test_admin_gets_the_full_view_even_if_they_confirmed`, `test_confirmer_gets_the_limited_view_without_notes`, `test_stranger_gets_not_visible`, `test_missing_report_gets_not_visible`.
- [ ] **Step 2:** FAIL → **Step 3:** implementar → **Step 4:** PASS.
- [ ] **Step 5: Pruebas de integración que fallan** (`test_report_detail_api.py`):
  - `test_author_sees_history_registered_then_evaluated` → `[h["status"] for h in history] == ["registrado", "evaluado"]` (usar los valores de `ReportStatus`).
  - `test_confirmer_sees_limited_view_and_notes_are_hidden` → tras un cambio de estado con observación insertado en `historial_estado`, `note` es `None` para quien confirmó y visible para el autor.
  - `test_stranger_gets_404_like_a_missing_report` → mismo cuerpo de error que un UUID inexistente.
  - `test_non_uuid_id_is_422` (Review Focus 2) → `GET /reports/abc` → 422.
- [ ] **Step 6:** infraestructura y ruta → suite completa PASS.
- [ ] **Step 7: Commit** en `feat/reports-detalle`: `feat(reports): detalle del reporte para autor, administrador y quien confirmó` con `Refs: HU-07, HU-12, HU-16`. Integrar.

---

### Task 5: Documentación y cierre del bloque de backend

**Files:**
- Modify: `AGENTS.md` (sección 6.2: añadir `GET /api/v1/reports/{id}` con su regla de acceso y quitar de «Queda para cuando lo pida el cliente» de la fase 5 lo construido), `README.md` (endpoints), `CHANGELOG.md` («Sin publicar»), `docs/bitacora.md` (decisión 49: B1–B3 aplicados).

- [ ] **Step 1:** Revisar el OpenAPI (`uv run python -c "from app.main import create_app; import json; print(json.dumps(create_app().openapi()['paths'], indent=1))"` o el equivalente del proyecto) y comprobar que las tres rutas nuevas y `is_mine` aparecen con sus respuestas de error.
- [ ] **Step 2:** Actualizar los documentos listados.
- [ ] **Step 3:** Suite completa → PASS; cobertura de dominio y aplicación ≥ 80 %.
- [ ] **Step 4: Commit** en `docs/backend-flujo-critico-app`: `docs: documentar confirmaciones, mis reportes y detalle` con `Refs: HU-16, decisión 49`. Integrar y verificar la CI en `main`.
