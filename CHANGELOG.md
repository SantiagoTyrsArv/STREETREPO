# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/); versionado [SemVer](https://semver.org/lang/es/).

## [Sin publicar]

### Añadido
- Revisión de seguridad de la fase 8 (`docs/seguridad/revision-fase-8.md`, fila 142) con pruebas que
  exigen el rol en todas las rutas `/admin` y `/evaluation` y protegen el log de datos personales.
- Límite global de solicitudes por IP (600 cada 5 min, `GLOBAL_REQUESTS_PER_IP` y
  `GLOBAL_WINDOW_SECONDS`; fila 140) y cupo de inicio de sesión configurable
  (`LOGIN_PER_IP_PER_5_MINUTES`).
- Página de presentación: cabeceras de seguridad y caché larga en Vercel (`landing/vercel.json`) y
  presupuesto de peso comprobado en la CI (`scripts/check-media-budget.ts`). El QR de descarga se
  carga aparte, solo cuando hay un APK publicado.
- Despliegue con HTTPS (HU-17): `infra/docker-compose.prod.yml` con Caddy como proxy inverso
  (Let's Encrypt, redirección a HTTPS, HSTS, tope de 11 MB por petición a la API), solo los
  puertos 80 y 443 publicados y la API en `APP_ENV=prod` confiando solo en la IP fija del proxy.
- Objetivo 4 de la tesis (HU-09), backend: zonas de validación desde GeoJSON (`zones-import`,
  `GET /api/v1/admin/zones`), cuentas de evaluador (`create-evaluator`), rondas de evaluación con
  reportes congelados (`/api/v1/admin/evaluation-rounds`), vista a ciegas y envío del orden del
  evaluador (`/api/v1/evaluation/current`), métricas de acuerdo (rho, tau, W de Kendall,
  coincidencia ±1 y prueba entre zonas, propuesta 114) y la ficha comparativa en CSV (`ficha`,
  `resumen`, `reportes` y `avisos`). Migración 0009 (ADR 0008).
- Objetivo 4, panel y app:
  - **Panel por rol:** el administrador gana la sección Comparación (Zonas, Rondas y Resultados,
    con las cuatro descargas en CSV); el evaluador solo ve Mis evaluaciones y la vista a ciegas
    (arrastrar con `@dnd-kit`, subir y bajar, minimapa y borrador en `sessionStorage`).
  - **App:** manda el `duplicate_warning_id` al confirmar o al crear de todos modos desde
    «Posible duplicado».
  - **API:**
    - `GET …/results` incluye la vía de cada reporte (`road_name`);
    - CORS expone `Content-Disposition`.
  - **Pruebas de punta a punta:** una ronda completa con Playwright.
- Registro de los avisos de «Posible duplicado» y de la decisión del ciudadano:
  `duplicate_warning_id` en `GET /api/v1/reports/nearby` y en el 409 de `POST /api/v1/reports`, y
  campo opcional del mismo nombre al crear con `create_anyway` y al confirmar.

### Cambiado
- Backend sin avisos de Sonar en el código de la aplicación (fila 138): sin cambios en la API.
- Pruebas del backend sin avisos de Sonar ni de Starlette (fila 139).
- Página de presentación: cada capítulo ocupa una pantalla y su animación corre sola al llegar,
  una vez por carga, con un imán de proximidad entre capítulos; «Pruébalo» cabe en una pantalla y
  las letras de la portada empiezan en ámbar. La página pasa de ~22 a 7,95 pantallas en el
  celular.
- Página de presentación: el HTML llega prerenderizado (`src/entry-server.tsx` y
  `scripts/prerender.ts`) y el cliente lo hidrata; sin JavaScript se leen todos los textos. LCP en
  producción de 3,1 s a 2,2 s (móvil, 4G lento, CPU ×4).
- El inicio de sesión del panel acepta administradores y evaluadores; a un ciudadano le responde
  `STAFF_ROLE_REQUIRED`. Un evaluador no puede crear ni confirmar reportes
  (`EVALUATOR_CANNOT_REPORT`).
- Confirmar un reporte (HU-16) exige la ubicación actual de quien confirma, y solo se acepta a
  50 m o menos del daño: **403** `CONFIRMATION_TOO_FAR` si está más lejos. La distancia se guarda en
  `confirmacion.distancia_m` (migración 0008). La app la envía desde la ficha del mapa (pide el
  permiso de ubicación si hace falta) y desde «Posible duplicado» (propuesta 112).

### Dependencias
- `scipy` 1.18.1 (y `scipy-stubs`) para las pruebas estadísticas del objetivo 4.
- Panel: `@dnd-kit/core` 6.3.1, `@dnd-kit/sortable` 10.0.0 y `@dnd-kit/utilities` 3.2.2 para
  ordenar las tarjetas de la vista a ciegas.
- Actualizaciones de Dependabot (fila 135 de la bitácora): uv 0.13.9, FastAPI 0.165.0,
  SQLAlchemy 2.1.9, Alembic 1.20.1, pydantic-settings 2.16.3, ruff 0.17.6; Node 26 LTS en la CI y
  en la imagen del panel; nginx-unprivileged 1.30.6 (estable); `@types/node` 26.6.6 y
  `typescript-eslint` 8.74.0 en el panel y la página; `sonarqube-scan-action` 8.5.0 y `setup-uv`
  10.3.3. TypeScript 7 y ESLint 10 se posponen hasta que sus dependientes los acepten. Dependabot
  vigila también `landing/`.
- `httpx2` 2.16.2 (desarrollo) para `starlette.testclient`.
- Segunda tanda (fila 136): `setup-uv` 10.4.0; `prettier` 3.10.1, `jsdom` 31.0.1, `vite` 8.3.8 y
  `@testing-library/jest-dom` 8.0.0 en el panel y la página; `@tanstack/react-query` 5.108.2.
  React 19 en la página se pospone.


### Retirado
- Página de presentación: el espacio del video promocional (botón «Ver el video», sección y
  configuración de YouTube). Ya no habrá video.

## [0.7.0] - 2026-11-22

Fase 7: la app ciudadana completa el perfil (conocer, actualizar y suprimir los datos, Ley 1581)
y el mapa de reportes con «Confirmar este daño», probados en el celular del responsable el
2026-11-22 (decisión 111). Incluye lo construido después de `v0.6.0`, también la página de
presentación, que sigue en construcción.

### Añadido
- `GET /api/v1/reports?bbox=…`: reportes del área visible para el mapa de la app, con la vista
  pública (sin autor, descripción ni foto; ubicación redondeada), filtro por estado, tope de 200 y
  60 consultas por minuto por usuario (decisión 93).
- App ciudadana: pestaña «Mapa» con los reportes del área visible, filtros por estado, ficha del
  reporte y «Confirmar este daño» desde la ficha; teselas de OpenStreetMap con atribución y
  proveedor configurable (`MAP_TILE_URL`) (decisión 95).
- App ciudadana: el perfil permite conocer y actualizar los datos (nombre y correo; cambiar el
  correo pide la contraseña actual) y solicitar la supresión de los datos con constancia
  (Ley 1581; decisiones 71 y 92).
- Página de presentación y descarga `landing/` (en construcción, decisiones 99 a 109): proyecto
  Vite + React con la identidad editorial de la página, la marca nueva (símbolo «SR» con la vía y
  el Galeras, favicon e ícono), el motor de secuencias de cuadros guiado por el *scroll*, los
  capítulos Apertura, Problema, Priorizar y Reparado con sus textos y sus escenas generadas con
  Higgsfield (secuencias WebP de 16 fps, `scripts/build-sequences.ts`), el teléfono 3D con capturas
  reales, el panel y la descarga. Desplegada en Vercel. Faltan las cabeceras (`vercel.json`), la
  revisión de medios y la prueba en el celular.
- Página de presentación: fondo vivo en WebGL que toma el color de cada capítulo y responde al
  mouse y al tacto (lente y onda), escenas que respiran con paralaje, botones con imán y brillo, e
  inclinación del teléfono 3D y del panel; todo se detiene con «reducir movimiento» (decisión 108).
- Página de presentación: textos vivos (fuentes variables que se engrosan cerca del puntero o del
  dedo, títulos que entran por líneas y se deforman con el puntero, fórmula U que se descifra y se
  rellena), portada con la escena dentro de «STREET REPO» e indicador «Desliza», lupa en el título
  de Reparado, calculadora de urgencia «Pruébalo» con la fórmula real, barra de progreso por
  capítulos, Descarga en verde y espacio para un video promocional de YouTube (oculto hasta tener
  el video; decisión 109).

### Seguridad
- `dnspython` 2.9.2 y `opentelemetry-api` 1.45.2 (dependencias transitivas del backend) por
  CVE-2026-128089 y CVE-2026-126360, que dejaban en rojo la auditoría de la CI (decisión 94).

## [0.6.0] - 2026-11-11

Fase 6: panel administrativo de la Secretaría para el objetivo 3 de la tesis (priorización, detalle
y estado, pesos del modelo), servido con Docker Compose y con datos de demostración. Incluye lo
construido después de `v0.5.0`: la app ciudadana con el flujo crítico y el backend que necesita.

### Corregido
- `POST /api/v1/reports` respondía 500 en la API desplegada: el proceso no registraba el modelo de
  `servicio_critico` y SQLAlchemy no resolvía la clave foránea de `evaluacion_prioridad`. Las
  pruebas no lo veían porque otras ya importaban todos los modelos; hallado en la prueba en el
  celular.

### Cambiado
- uv 0.13.5 (antes 0.13.1) en la imagen de la API, en la CI y en desarrollo: Dependabot dejó de
  aceptar 0.13.1 y no abría actualizaciones del backend (decisión 73).
- Límites por IP más holgados por el CGNAT de los operadores móviles (decisión 58): registro 30 por
  hora (antes 10; ahora configurable con `REGISTER_PER_IP_PER_HOUR`) y reportes 100 por hora (antes
  30). Los límites por usuario y por correo no cambian.

### Añadido
- Panel administrativo web (`admin-web/`, React + TypeScript + Leaflet): inicio de sesión de
  funcionarios; Priorización con indicadores Activos · Evaluados · Priorizados · Reparados
  (propuesta 75), mapa de calor con leyenda y ranking paginado con S, F, P y U (HU-08); Detalle y
  estado con evidencia, vía OSM, desglose del cálculo, cambio de estado con observación e historial
  (HU-12); Pesos del modelo con validación Σ = 1,00, reglas en solo lectura y versiones (HU-14).
- API del panel, solo para administradores: `GET /api/v1/admin/ranking`, `/admin/summary` y
  `/admin/heatmap`; `GET /api/v1/admin/reports/{id}` y `PATCH /api/v1/admin/reports/{id}/status`
  (409 si la transición ya no es válida); `GET` y `PUT /api/v1/admin/weights` (409
  `WEIGHTS_VERSION_CONFLICT` si otro administrador guardó antes) y `GET /api/v1/admin/weights/versions`.
- Sesión web del panel (decisión 42): `/api/v1/auth/web/login`, `/refresh` y `/logout` con el
  refresco en una cookie `HttpOnly`, `Secure` y `SameSite=Strict`, defensa CSRF y acceso en memoria.
- App ciudadana Flutter para Android con el flujo crítico (decisión 49): registro con la política de
  datos, inicio de sesión, reporte con foto, GPS y severidad, posible duplicado (confirmar o crear),
  Mis reportes, detalle y perfil mínimo. Cómo ejecutarla en un celular, en `mobile/README.md`.
- `API_BIND_ADDRESS` en Docker Compose para publicar la API en la red local durante la prueba en
  el celular (por defecto `127.0.0.1`).
- `POST /api/v1/reports/{id}/confirmations` (HU-16): confirmar un reporte activo de otro
  ciudadano; 409 si está reparado, es propio (propuesta 48) o ya se confirmó. No cambia U.
- `GET /api/v1/me/reports`: reportes creados y confirmados, paginados (decisión 49).
- `GET /api/v1/reports/{id}`: detalle con historial para el autor, los administradores y, en
  vista pública sin observaciones, quien lo confirmó; 404 para los demás.
- `POST /api/v1/reports` responde 422 `IDEMPOTENCY_KEY_REUSED` si la clave llega con otros datos
  (decisión 46a) y 413 `PHOTO_TOO_LARGE` por `Content-Length` antes de recibir la foto (46d).
- `infra/scripts/test-integration.sh`: pruebas de integración con PostGIS en un comando (46b).
- `is_mine` en los candidatos de `GET /api/v1/reports/nearby` y del 409 `REPORT_DUPLICATE_NEARBY`
  (propuesta 48).
- `python -m app.cli seed-demo` y `seed-demo --remove`: 32 reportes de demostración para el panel
  sobre vías reales, evaluados por el motor real, con cuentas `@demo.invalid` sin acceso y fotos
  generadas. No son datos de campo (decisión 76).
- El panel administrativo se sirve con Docker Compose (servicio `admin-web`, nginx sin root en
  `http://localhost:8080`) con CSP y cabeceras de seguridad; la CI construye su imagen.
- Pruebas de punta a punta del panel con Playwright (`infra/scripts/e2e-panel.sh`), en un stack
  aparte que no toca la base de desarrollo.

## [0.5.0] - 2026-10-19

Fase 5 (reducida por la decisión 44): reportes ciudadanos con foto, deduplicación a 25 m y
fotos en la supresión de datos.

### Añadido
- `GET /api/v1/reports/{id}/photo` y `/photo/thumbnail`: la foto y su miniatura en JPEG, solo para el
  autor y los administradores; 404 para los demás y `Cache-Control: private, no-store` (propuesta 34).
- Supresión de datos (Ley 1581): borra también las fotos y miniaturas de los reportes del titular;
  los archivos se borran tras confirmar, con reintentos, y el comando
  `python -m app.cli purge-orphan-photos` recoge los que queden sin referencia (propuesta 39).
- Migración 0007: `reporte.clave_idempotencia`, única por par (usuario, clave) (propuesta 11).
- `POST /api/v1/reports`: crea el reporte con foto, ubicación, severidad y descripción, y lo
  evalúa en la misma transacción (queda «evaluado» con U, dirección y «Revisar vía»). Con
  `Idempotency-Key`, un reintento responde 200 con el reporte existente (propuesta 11).
- Fotos: tipo real JPEG, PNG o WebP, hasta 10 MB y 50 MP; se recodifican a JPEG sin metadatos
  (1600 px y miniatura de 400 px) y se guardan en disco, en el volumen `photos` de Compose
  (propuestas 34 y 35). Dependencias nuevas: `pillow` y `python-multipart`.
- Área de servicio `REPORT_AREA_BBOX` (422 fuera de ella) y límite de 10 reportes por hora por
  usuario y 30 por IP, configurables (propuestas 37 y 38).
- La dirección del reporte es el nombre de la vía OSM asociada, con texto de reserva (propuesta 41).
- README: sección de respaldos de la base y de las fotos.
- Posible duplicado (HU-15): `GET /api/v1/reports/nearby` lista los reportes activos a 25 m sin
  datos del autor, y `POST /api/v1/reports` responde 409 `REPORT_DUPLICATE_NEARBY` con ellos salvo
  `create_anyway=true`. Un candado de transacción evita que dos envíos simultáneos esquiven la
  verificación; un reintento con la misma `Idempotency-Key` sigue respondiendo 200 (propuesta 36).

### Corregido
- `GET /api/v1/reports/nearby` y el 409 de duplicado ya no permiten calcular la ubicación exacta de
  reportes ajenos: devuelven la ubicación redondeada a 4 decimales y la distancia medida desde ella.
  `nearby` exige un punto dentro del área de servicio y tiene un cupo por usuario (propuesta 43).
- Las migraciones de Alembic ya no desactivan los loggers de la aplicación creados antes de migrar.

## [0.4.0] - 2026-10-17

Fase 4: autenticación y usuarios.

### Añadido
- Migración 0006: `usuario.version_politica`, `token_refresco` y `solicitud_supresion` (propuestas 8, 9 y 10).
- Autenticación: registro de ciudadanos con consentimiento de la versión vigente de la política,
  inicio de sesión con Argon2id, JWT de acceso de 15 min y refresco rotatorio con detección de
  reutilización, cierre de sesión, `GET /api/v1/me` y control de acceso por rol en el servidor.
- Comando `python -m app.cli create-admin` para crear administradores.
- Análisis de SonarQube Cloud en la CI con la cobertura del backend (propuesta 22).
- Límite de intentos: bloqueo progresivo del inicio de sesión por correo tras 5 fallos seguidos
  (1, 2, 4, 8 y hasta 15 min) y límite por IP en inicio de sesión (30 cada 5 min) y registro
  (10 por hora); responden 429 con `Retry-After` (decisión 25).
- Derechos del titular (Ley 1581): `PATCH /api/v1/me` para actualizar nombre y correo, y
  `POST /api/v1/me/data-deletion-requests` para suprimir los datos de inmediato por anonimización
  (conserva los reportes, borra su descripción, revoca las sesiones y deja la constancia atendida).
  Suprimir la cuenta o cambiar el correo exige la contraseña actual (propuesta 26).
- `GET /api/v1/privacy-policy`, pública: versión vigente de la política de datos y su dirección
  (`PRIVACY_POLICY_URL`, obligatoria y con https en producción) (propuestas 27 y 33).
- `FORWARDED_ALLOW_IPS` configurable: la API no arranca si vale `*`; uvicorn corre con
  `--workers 1` (condiciones de la decisión 25).

### Cambiado
- La CI corre también al subir ramas de trabajo, no solo con *push* a `main`.
- CI: `actions/checkout` v7.0.1, `astral-sh/setup-uv` v10.3.0, `actions/upload-artifact` v7.0.2 y
  `actions/download-artifact` v8.0.2, que ya corren en Node 24 (quitan el aviso de Node 20 obsoleto).
  La descarga del informe de cobertura falla si su hash no coincide.
- Dependabot ya no propone Python 3.14 o superior (decisión 2: Python 3.13).
- La versión de la API vive solo en `app/__init__.py` (`__version__`), la usan OpenAPI y
  `/health` y `/ready` (campo `version`), y una prueba la compara con `pyproject.toml` (decisión 30a).
- El job `sonar` no corre en las ramas de Dependabot, que no reciben `SONAR_TOKEN` (propuesta 32).
- En `main`, el job `sonar` espera la puerta de calidad y falla si no pasa (propuesta 28).
- pre-commit rechaza marcadores de conflicto sin resolver (`check-merge-conflict`, propuesta 31).
- uv 0.13.1 en la imagen de la API, en la CI y en desarrollo, fijado con `required-version` en
  `pyproject.toml`; una prueba verifica que el Dockerfile use la misma versión.
- `uv.lock` en el formato de uv 0.13 (`revision = 5`), sin cambios de paquetes; la CI comprueba con
  `uv lock --check` que el lock corresponda a `pyproject.toml`.

### Corregido
- El inicio de sesión tardaba el doble con un correo inexistente, lo que permitía saber si una
  cuenta existía; ahora tarda lo mismo (decisión 29a).
- Hallazgos de SonarQube Cloud que tumbaban la puerta de calidad, entre ellos CORS como capa más
  externa para que sus cabeceras lleguen también en los errores (decisión 29b).

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

[Sin publicar]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.5.0...HEAD
[0.6.0]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/SantiagoTyrsArv/STREETREPO/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/SantiagoTyrsArv/STREETREPO/releases/tag/v0.1.0
