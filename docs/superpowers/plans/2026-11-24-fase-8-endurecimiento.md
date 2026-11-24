# Fase 8 — Endurecimiento: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dejar evidencia verificable de seguridad, accesibilidad y rendimiento para la sustentación, con Sonar en cero avisos y un límite global por IP, y cerrar la fase con `v0.8.0`.

**Architecture:** Cambios pequeños y separados por rama (guía 8.4). El límite global es un *middleware* ASGI que reutiliza el `RateLimiter` en memoria que ya existe. Las revisiones de accesibilidad son pruebas (axe con Playwright en el panel; pautas de Flutter en la app). La carga usa Locust contra el stack local de Docker Compose, con cuentas de carga que se crean y se borran con la CLI.

**Tech Stack:** FastAPI, pytest, Playwright + `@axe-core/playwright`, Flutter `flutter_test`, Locust.

**Spec:** `docs/superpowers/specs/2026-11-24-fase-8-endurecimiento-design.md`

## Global Constraints

- Una rama por tarea, desde `main` actualizada; integración con `git merge --no-ff` sin PR; borrar la rama al integrar (guía 8.4).
- Antes de cada commit: `ruff check`, `ruff format --check`, `mypy` y `pytest` del backend; `npm run lint`, `format:check`, `typecheck` y `vitest` del panel; `flutter analyze` y `flutter test` de la app, según lo tocado.
- Commits en Conventional Commits, en español, con qué, por qué y cómo se verificó, y la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Cada tarea añade su fila a `docs/bitacora.md` (138 en adelante) y su línea al CHANGELOG en «Sin publicar».
- Interfaz y documentos en español de Colombia; identificadores en inglés.
- Las cifras de carga son **medidas del sistema en un equipo local**, nunca resultados de campo ni del capítulo 4.
- Los cupos solo se suben con variables de entorno del entorno de carga o de E2E; los valores por defecto no se tocan para que una prueba pase.
- Un hallazgo de accesibilidad que exija cambiar el diseño aprobado (colores, textos, distribución) no se aplica: se propone con el protocolo 0.3 de la guía.
- Cuentas de carga solo con el dominio `@carga.invalid`; nada de datos personales en informes ni logs.

## Review Focus

1. **Muchos ciudadanos detrás de la misma IP (NAT de la universidad o del operador móvil):** el cupo global por defecto (600 cada 5 min) no debe cortar un uso normal del panel ni de la app. Prueba en la tarea 3: 600 solicitudes seguidas pasan; la 601 da 429.
2. **Petición sin dirección de cliente** (`scope["client"]` es `None`, p. ej. algunos servidores de prueba): el *middleware* no falla y cuenta contra la clave `desconocido`. Prueba en la tarea 3.
3. **Una solicitud rechazada no consume cupo:** tras el 429, al pasar la ventana se vuelve a atender. Prueba en la tarea 3 con un reloj controlado.
4. **Las sondas no se cortan nunca:** `/health` y `/ready` responden aunque la IP haya agotado el cupo (Docker marcaría el contenedor como enfermo). Prueba en la tarea 3.
5. **Borrar las cuentas de carga deja la base y el disco limpios:** `loadtest-accounts --remove` borra usuarios, reportes, evaluaciones, historial y archivos de fotos; un segundo `--remove` no falla. Prueba en la tarea 7.

---

### Task 1: Sonar en cero — código de la aplicación

Rama: `refactor/backend-avisos-sonar-app`.

**Files:**
- Modify: los archivos de `backend/app/` que lista Sonar (los `router.py` y `*_router.py` con S8409; `validation/infrastructure/models.py` con S1192; `validation/domain/rounds.py` y `auth/presentation/schemas.py` con S7632; los de S7503, S5713, S7492, S8997 y S1135).

**Interfaces:**
- Produces: nada que usen otras tareas.

- [ ] **Step 1: Listar los avisos abiertos de `backend/app`**

Run: `curl -s "https://sonarcloud.io/api/issues/search?componentKeys=SantiagoTyrsArv_STREETREPO&resolved=false&ps=500" | python -c "import json,sys;[print(i['rule'],i['component'].split(':')[-1],i.get('line')) for i in json.load(sys.stdin)['issues'] if '/app/' in i['component']]"`
Expected: la lista de avisos de la aplicación (unos 46). Guardarla en el cuerpo del commit.

- [ ] **Step 2: Guardar el OpenAPI actual como referencia**

Run: `cd backend && uv run python -c "import json;from app.main import create_app;print(json.dumps(create_app().openapi(),sort_keys=True,indent=1))" > ../.superpowers/openapi-antes.json`
Expected: archivo creado (fuera de git).

- [ ] **Step 3: Corregir cada aviso sin cambiar el comportamiento**

S8409: quitar `response_model=` solo donde la anotación de retorno es el mismo modelo. S1192: constantes con nombre para `"usuario.id_usuario"` y `"reporte.id_reporte"` en `models.py`. S7632: la sintaxis de supresión que pide Sonar (`# NOSONAR` o el formato documentado de la regla). El resto, según el mensaje de cada regla.

- [ ] **Step 4: Comprobar que el contrato de la API no cambió**

Run: repetir el comando del paso 2 con salida `../.superpowers/openapi-despues.json` y luego `diff ../.superpowers/openapi-antes.json ../.superpowers/openapi-despues.json && echo IGUAL`
Expected: `IGUAL`. No se guarda una instantánea en el repositorio: sería ruido en cada cambio legítimo de la API.

- [ ] **Step 5: Verificar la suite completa**

Run: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && cd .. && infra/scripts/test-integration.sh -q`
Expected: todo limpio; 1002 pruebas o más, todas OK.

- [ ] **Step 6: Commit, bitácora, *merge* y comprobar en Sonar**

Tras la CI en `main`, la consulta del paso 1 no debe devolver avisos de `backend/app`.

---

### Task 2: Sonar en cero — pruebas, y aviso de Starlette

Rama: `test/backend-avisos-sonar-pruebas`.

**Files:**
- Modify: los archivos de `backend/tests/` que lista Sonar (S5778 en 53 lugares, la mayoría en `test_validation_blind.py`, `test_zones_api.py`, `test_validation_rounds.py`, `test_validation_zones.py`, `test_create_report.py`).
- Modify: `backend/pyproject.toml` (dependencia de desarrollo o filtro del aviso).

- [ ] **Step 1: Corregir S5778**

En cada `with pytest.raises(...)`, dejar dentro solo la llamada que debe lanzar; preparar los argumentos antes del bloque. No cambiar qué se prueba.

- [ ] **Step 2: Resolver el aviso `StarletteDeprecationWarning` de `starlette.testclient`**

Leer el aviso y la documentación de la versión de Starlette instalada. Si pide `httpx2`, añadirlo como dependencia de desarrollo con `uv add --dev` y comprobar que `TestClient` lo usa; si eso exige cambios en las pruebas que no aportan, filtrar ese aviso concreto en `[tool.pytest.ini_options] filterwarnings` con un comentario que explique por qué. Registrar la elección en la bitácora.

- [ ] **Step 3: Verificar**

Run: `cd .. && infra/scripts/test-integration.sh -q -W error::DeprecationWarning`
Expected: todas OK y `0 warnings` (o solo avisos ajenos a Starlette, que se anotan).

- [ ] **Step 4: Commit, *merge* y comprobar que Sonar queda en 0 avisos abiertos**

Run (tras la CI en `main`): la consulta de la tarea 1, paso 1, sin el filtro `/app/`.
Expected: `total` igual a 0.

---

### Task 3: Límite global de solicitudes por IP

Rama: `feat/core-limite-global`.

**Files:**
- Create: `backend/app/core/global_rate_limit.py`
- Modify: `backend/app/core/config.py`, `backend/app/main.py`, `backend/app/core/rate_limiting.py` (cupo de login configurable), `.env.example`, `README.md`, `infra/scripts/e2e-panel.sh` (subir el cupo en E2E si hace falta)
- Test: `backend/tests/unit/test_global_rate_limit.py`, `backend/tests/integration/test_global_rate_limit_api.py`

**Interfaces:**
- Consumes: `RateLimit`, `RateLimiter`, `RateLimitExceededError` (`app/shared/application/rate_limit.py`); `retry_after_seconds` (`app/core/rate_limiting.py`); `error_body` (`app/core/errors.py`); `Clock` y `SystemClock` (`app/shared/application/clock.py`).
- Produces:
  - `Settings.global_requests_per_ip: int = Field(default=600, ge=1)`, `Settings.global_window_seconds: int = Field(default=300, ge=1)` (variables `GLOBAL_REQUESTS_PER_IP` y `GLOBAL_WINDOW_SECONDS`).
  - `Settings.login_per_ip_per_5_minutes: int = Field(default=30, ge=1)` (variable `LOGIN_PER_IP_PER_5_MINUTES`); reemplaza la constante `LOGIN_LIMIT_PER_IP`. La tarea 8 la sube en el entorno de carga.
  - `GLOBAL_RATE_LIMIT_EXEMPT_PATHS: Final[frozenset[str]] = frozenset({"/health", "/ready", "/docs", "/openapi.json"})`
  - `class GlobalRateLimitMiddleware: __init__(self, app: ASGIApp, *, limiter: RateLimiter, limit: RateLimit, clock: Clock, exempt_paths: frozenset[str] = GLOBAL_RATE_LIMIT_EXEMPT_PATHS)`

- [ ] **Step 1: Escribir las pruebas unitarias que fallan** (app mínima de Starlette con una ruta `/ping`, `/health` y `InMemoryRateLimiter` con reloj falso)

```python
def test_allows_requests_up_to_the_limit(): ...        # 3 de cupo: las 3 primeras → 200
def test_rejects_with_429_and_retry_after(): ...       # la 4.ª → 429, body["code"] == "RATE_LIMITED",
                                                       # body["details"]["retry_after_s"] >= 1, cabecera Retry-After
def test_exempt_paths_are_never_limited(): ...         # cupo agotado → GET /health sigue en 200
def test_rejected_request_does_not_consume_quota(): ...# tras la ventana (reloj + window) → 200 otra vez
def test_counts_per_client_ip(): ...                   # otra IP con el cupo de la primera agotado → 200
def test_missing_client_uses_unknown_key(): ...        # scope["client"] = None → sin excepción, cuenta
def test_ignores_non_http_scopes(): ...                # scope lifespan/websocket pasa sin contar
```

Mensaje del 429, exacto: «Demasiadas solicitudes desde tu conexión. Intenta de nuevo en unos minutos.»

- [ ] **Step 2: Ejecutar y ver que fallan**

Run: `cd backend && uv run pytest tests/unit/test_global_rate_limit.py -v`
Expected: FAIL (`ModuleNotFoundError: app.core.global_rate_limit`).

- [ ] **Step 3: Implementar el *middleware* y la configuración**

Clave del limitador: `f"global:{ip}"`. En `create_app`, añadirlo **justo después** de `BodySizeLimitMiddleware`, para que su 429 lleve CORS, cabeceras de seguridad y log. `RateLimit(max_requests=settings.global_requests_per_ip, window=timedelta(seconds=settings.global_window_seconds))`, `limiter=app.state.rate_limiter`, `clock=SystemClock()`. Cambiar el login para leer `login_per_ip_per_5_minutes` de `Settings`.

- [ ] **Step 4: Prueba de integración**

`test_global_rate_limit_api.py::test_global_limit_applies_to_api_routes`: `create_app` con `global_requests_per_ip=2`; dos `GET /api/v1/privacy-policy` → 200; la tercera → 429 con `Access-Control-Allow-Origin` para el origen permitido y `X-Content-Type-Options: nosniff`.

- [ ] **Step 5: Verificar la suite completa, incluidas las E2E del panel**

Run: `cd backend && uv run ruff check . && uv run mypy && cd .. && infra/scripts/test-integration.sh -q && infra/scripts/e2e-panel.sh`
Expected: todo OK. Si una E2E recibe 429, subir `GLOBAL_REQUESTS_PER_IP` solo en `e2e-panel.sh`.

- [ ] **Step 6: Documentar y hacer el commit**

`.env.example` con las tres variables y un comentario sobre NAT; README, sección de configuración; bitácora (decisión 30c aplicada) y CHANGELOG. *Merge* y borrar la rama.

---

### Task 4: Revisión de seguridad (guía 15)

Rama: `docs/seguridad-revision-fase-8`; cada corrección, en su rama `fix/…`.

**Files:**
- Create: `docs/seguridad/revision-fase-8.md`

- [ ] **Step 1: Levantar el stack local y recoger la evidencia automática**

Run: `docker compose -f infra/docker-compose.yml --env-file .env up -d --build --wait` y luego:
`cd backend && uv export --frozen --no-dev --no-hashes -o ../.superpowers/req.txt && uv run pip-audit -r ../.superpowers/req.txt`; `cd admin-web && npm audit --audit-level=high`; `cd landing && npm audit --audit-level=high`; `cd mobile && flutter pub outdated`; `curl -sI http://127.0.0.1:8000/health` y `curl -sI http://127.0.0.1:8080/`.
Expected: salidas guardadas para citar en el informe.

- [ ] **Step 2: Recorrer los 11 puntos de la sección 15 de la guía**

Para cada punto, la evidencia concreta: archivo y línea, la prueba que lo demuestra (nombre exacto) o la salida del paso 1. Puntos que dependen de un servidor (HTTPS real, HSTS en el proxy): estado «Configurado, sin desplegar», con remisión a `infra/docker-compose.prod.yml` y a la fila 121.

- [ ] **Step 3: Corregir cada punto que falle**

Una rama `fix/…` por hallazgo, con prueba que lo cubra, integrada antes de cerrar el informe. Si no hay hallazgos, el informe lo dice.

- [ ] **Step 4: Escribir el informe**

Estructura: alcance y fecha; tabla «Punto · Estado (Cumple / Corregido en esta fase / Configurado, sin desplegar / Pendiente) · Evidencia»; salidas de las herramientas resumidas; Sonar (0 avisos, 0 vulnerabilidades, 0 *hotspots* tras las tareas 1 y 2); «Fuera de alcance»; lo pendiente con su decisión de la bitácora.

- [ ] **Step 5: Commit, bitácora, *merge* y bajar el stack**

---

### Task 5: Accesibilidad del panel con axe

Rama: `test/admin-web-accesibilidad`.

**Files:**
- Modify: `admin-web/package.json` (dependencia de desarrollo `@axe-core/playwright`, versión exacta)
- Create: `admin-web/e2e/accesibilidad.spec.ts`
- Modify: los componentes del panel que axe señale

**Interfaces:**
- Consumes: el *login* y los datos de las E2E existentes (`admin-web/e2e/panel.spec.ts`, `validation.spec.ts`): reutilizar sus funciones de ayuda en vez de copiarlas.

- [ ] **Step 1: Escribir la prueba**

Una prueba por pantalla, cada una con `new AxeBuilder({ page }).withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa","wcag22aa"]).analyze()` y
```ts
expect(results.violations.filter(v => v.impact === "serious" || v.impact === "critical")).toEqual([]);
```
Pantallas: inicio de sesión (con el error de credenciales visible), Priorización, Detalle y estado, Pesos (con el error de suma ≠ 1,00 visible), Comparación › Zonas, Rondas y Resultados, y la vista del evaluador.

- [ ] **Step 2: Ejecutar y ver qué falla**

Run: `infra/scripts/e2e-panel.sh e2e/accesibilidad.spec.ts`
Expected: la lista de hallazgos serios o críticos (anotarla).

- [ ] **Step 3: Corregir**

Cada corrección con su prueba de Vitest y Testing Library cuando aplique (p. ej. etiqueta asociada, nombre accesible). Lo que exija cambiar el diseño aprobado se anota como propuesta y la prueba lo excluye con `.disableRules([...])` y un comentario `TODO(propuesta-N)`.

- [ ] **Step 4: Verificar**

Run: `cd admin-web && npm run lint && npm run typecheck && npx vitest run && cd .. && infra/scripts/e2e-panel.sh`
Expected: todo OK, incluida `accesibilidad.spec.ts`.

- [ ] **Step 5: Commit, bitácora (decisión menor: `@axe-core/playwright`), *merge***

---

### Task 6: Accesibilidad de la app con las pautas de Flutter, e informe

Rama: `test/mobile-accesibilidad`.

**Files:**
- Create: `mobile/test/accessibility/guidelines_test.dart`
- Modify: los *widgets* que las pautas señalen
- Create: `docs/accesibilidad/revision-fase-8.md`

**Interfaces:**
- Consumes: los dobles de `mobile/test/support/` (`fake_auth_repository.dart`, `fake_new_report_repository.dart`, `fake_report_map_repository.dart`, `fake_my_reports_repository.dart`, `fake_device_services.dart`, `load_fonts.dart`).

- [ ] **Step 1: Escribir la prueba**

Una prueba por pantalla, con `tester.ensureSemantics()` y
```dart
await expectLater(tester, meetsGuideline(androidTapTargetGuideline));
await expectLater(tester, meetsGuideline(iOSTapTargetGuideline));
await expectLater(tester, meetsGuideline(labeledTapTargetGuideline));
await expectLater(tester, meetsGuideline(textContrastGuideline));
```
Pantallas: Bienvenida, Iniciar sesión, Registro, Política de datos, Nuevo reporte (Foto y ubicación; Severidad), Posible duplicado, Reporte enviado, Mis reportes, Detalle del reporte, Mapa (ficha abierta) y Perfil. El mapa puede excluir las teselas (sin red en la prueba).

- [ ] **Step 2: Ejecutar y ver qué falla**

Run: `cd mobile && flutter test test/accessibility/guidelines_test.dart`
Expected: la lista de fallos (anotarla).

- [ ] **Step 3: Corregir** con la misma regla del diseño aprobado que la tarea 5.

- [ ] **Step 4: Verificar**

Run: `cd mobile && flutter analyze && dart format --set-exit-if-changed . && flutter test`
Expected: todo OK.

- [ ] **Step 5: Escribir el informe de accesibilidad**

`docs/accesibilidad/revision-fase-8.md`: alcance (WCAG 2.2 AA), herramientas, resultados del panel (tarea 5) y de la app, correcciones, propuestas pendientes y una lista corta para que el responsable revise con TalkBack en su celular (registro, nuevo reporte, confirmar en el mapa).

- [ ] **Step 6: Commit, bitácora, *merge***

---

### Task 7: Cuentas de carga en la CLI

Rama: `test/backend-carga-locust` (la tarea 8 sigue en la misma rama: un solo objetivo, las pruebas de carga).

**Files:**
- Create: `backend/app/modules/admin/application/loadtest_accounts.py` (o el módulo donde vive `SeedDemo`, siguiendo su patrón)
- Modify: `backend/app/cli.py`
- Test: `backend/tests/integration/test_loadtest_accounts.py`

**Interfaces:**
- Consumes: el patrón de `SeedDemo` (`_build_seed_demo`, `_seed_demo(remove=...)` en `app/cli.py`), el hasher de contraseñas y el almacenamiento de fotos que ya usa `seed-demo --remove`.
- Produces:
  - `LOADTEST_EMAIL_DOMAIN: Final = "carga.invalid"`
  - `class LoadTestAccounts: create(self, count: int, password: str) -> list[str]` (correos `carga-001@carga.invalid`… con política aceptada y rol ciudadano) y `remove(self) -> int` (usuarios borrados, con sus reportes, confirmaciones, evaluaciones, historial, tokens y archivos de fotos).
  - Comando: `python -m app.cli loadtest-accounts --count N` (contraseña desde la variable `LOADTEST_PASSWORD`, obligatoria; nunca por argumento) y `python -m app.cli loadtest-accounts --remove`.

- [ ] **Step 1: Escribir las pruebas de integración que fallan**

```python
def test_create_makes_citizen_accounts_that_can_log_in(): ...   # 3 cuentas; login con la contraseña → 200
def test_create_is_idempotent(): ...                             # crear 3 y luego 3 → siguen siendo 3
def test_remove_deletes_accounts_reports_and_photo_files(): ...  # con un reporte con foto → 0 filas y archivo borrado
def test_remove_twice_does_not_fail(): ...                       # segundo remove → 0
def test_remove_does_not_touch_other_users(): ...                # un usuario normal sigue existiendo
```

- [ ] **Step 2: Ejecutar y ver que fallan**

Run: `infra/scripts/test-integration.sh tests/integration/test_loadtest_accounts.py -v`
Expected: FAIL (comando o clase inexistente).

- [ ] **Step 3: Implementar** siguiendo el patrón de `SeedDemo`: una transacción para las filas, archivos borrados después del commit.

- [ ] **Step 4: Verificar la suite completa**

Run: `cd backend && uv run ruff check . && uv run mypy && cd .. && infra/scripts/test-integration.sh -q`
Expected: todo OK.

- [ ] **Step 5: Commit** (sin integrar todavía; la rama sigue con la tarea 8)

---

### Task 8: Pruebas de carga con Locust e informe

Misma rama que la tarea 7.

**Files:**
- Modify: `backend/pyproject.toml` (`locust` como dependencia de desarrollo, versión exacta; decisión 68)
- Create: `backend/loadtests/locustfile.py`, `backend/loadtests/README.md`
- Create: `infra/scripts/load-test.sh`
- Create: `docs/rendimiento/informe-carga-fase-8.md`

**Interfaces:**
- Consumes: `loadtest-accounts` (tarea 7); `LOGIN_PER_IP_PER_5_MINUTES`, `GLOBAL_REQUESTS_PER_IP` (tarea 3); `REPORTS_PER_USER_PER_HOUR`, `REPORTS_PER_IP_PER_HOUR`, `MAP_REQUESTS_PER_USER_PER_MINUTE` (`config.py`).

- [ ] **Step 1: Escribir `locustfile.py`**

- `CitizenUser` (peso 9): al empezar, inicia sesión con la siguiente cuenta `carga-NNN@carga.invalid`; tareas con pesos `GET /api/v1/reports` con un *bounding box* de Pasto (5), `GET /api/v1/reports/nearby` en un punto con vía (3), `POST /api/v1/reports` con una foto JPEG pequeña generada en memoria con Pillow, severidad al azar, `Idempotency-Key` nuevo y `create_anyway=true` (1); `wait_time = between(1, 3)`.
- `AdminUser` (peso 1): sesión de administrador (credenciales por variables de entorno); `GET /api/v1/admin/ranking` (2) y `GET /api/v1/admin/heatmap` (1).
- Nombres de solicitud agrupados (`name="/api/v1/reports [bbox]"`, etc.) para que el informe tenga una fila por endpoint.

- [ ] **Step 2: Escribir `infra/scripts/load-test.sh`**

Levanta un proyecto de Compose aparte (`street-repo-load`, como `e2e-panel.sh`) con los cupos subidos **solo ahí** (`GLOBAL_REQUESTS_PER_IP`, `LOGIN_PER_IP_PER_5_MINUTES`, `REPORTS_PER_*`, `MAP_REQUESTS_PER_USER_PER_MINUTE`), carga OSM la primera vez y `seed-demo`, crea 60 cuentas con `loadtest-accounts`, corre `uv run locust --headless -u 50 -r 5 -t 5m --csv ../.superpowers/carga/resultado --host http://localhost:<puerto>` y al final ejecuta `loadtest-accounts --remove` y `seed-demo --remove` (también si Locust falla, con `trap`).

- [ ] **Step 3: Prueba de humo corta**

Run: `infra/scripts/load-test.sh -t 30s -u 5`
Expected: sin errores 4xx/5xx salvo los esperados; las cuentas de carga desaparecen al terminar (comprobar con `SELECT count(*) FROM usuario WHERE correo LIKE '%@carga.invalid'` → 0).

- [ ] **Step 4: Corrida completa**

Run: `infra/scripts/load-test.sh`
Expected: los CSV de Locust en `.superpowers/carga/`.

- [ ] **Step 5: Escribir el informe**

`docs/rendimiento/informe-carga-fase-8.md`. Primera línea, exacta: «Medidas del sistema en un equipo local con datos de demostración; no son resultados de campo ni del capítulo 4.» Luego: equipo (CPU, RAM, sistema operativo, Docker), configuración exacta (usuarios, rampa, duración, cupos subidos), el comando para repetirla, una tabla por endpoint (solicitudes, errores, p50, p95, máximo, solicitudes/s) y la comparación con las metas de la guía 11 (listados < 500 ms; envío de reporte < 3 s). Una meta no cumplida se registra tal cual y se propone su mejora con el protocolo 0.3; la meta no se cambia.

- [ ] **Step 6: Verificar, hacer el commit, bitácora (decisión 68 aplicada), *merge***

Run: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy`
Expected: limpio (añadir `loadtests/` a ruff y mypy si no lo cubren).

---

### Task 9: Cierre de la fase 8

Rama: `chore/cierre-fase-8`.

**Files:**
- Modify: `README.md`, `CHANGELOG.md`, `AGENTS.md` (sección 13: estado de la fase 8), `backend/pyproject.toml`, `backend/app/__init__.py`, `admin-web/package.json` (versión `0.8.0`), `docs/bitacora.md`

- [ ] **Step 1: README**: límite global (variables), cómo correr la carga (`infra/scripts/load-test.sh`), la revisión de axe y los tres informes.
- [ ] **Step 2: Versión 0.8.0** en backend (`pyproject.toml` y `app/__init__.py`, que comprueba `test_tool_versions.py`) y en el panel; CHANGELOG: mover «Sin publicar» a `[0.8.0] - <fecha>` (incluye el objetivo 4, que no tenía versión).
- [ ] **Step 3: Verificar todo**

Run: backend (`ruff`, `mypy`, `infra/scripts/test-integration.sh`), panel (`lint`, `typecheck`, `vitest`, `build`), página (`lint`, `typecheck`, `vitest`), app (`flutter analyze`, `flutter test`).
Expected: todo OK; anotar los números de pruebas para la bitácora y el informe al responsable.

- [ ] **Step 4: *Merge*, CI en verde en `main`, etiqueta**

Run: `git tag -a v0.8.0 -m "Fase 8: endurecimiento para la sustentación" && git push origin v0.8.0`

- [ ] **Step 5: Linear y evidencia**

Mover las historias de la fase a hecho con capturas (informe de carga, salida de axe, Sonar en cero) en un comentario, según la memoria de evidencia fotográfica.
