# Revisión de seguridad — fase 8

> 2026-11-24 · guía, sección 15 · bitácora, filas 140 a 142 · versión revisada: `main` en `d421860`

## Alcance

Se recorrió la lista de verificación de seguridad de la sección 15 de la guía contra el código,
las pruebas automáticas y el stack local levantado con Docker Compose (`db`, `api`, `admin-web`).
Cada punto lleva su **evidencia**: el archivo, la prueba que lo demuestra o la salida de una
herramienta, de modo que se pueda repetir.

El sistema corre hoy solo en local y en el celular del responsable (fila 123): lo que depende de
un servidor público se marca «Configurado, sin desplegar». La app móvil y la página de
presentación se revisaron en lo que toca a esta lista (tokens y dependencias).

## Resultado

| # | Punto de la guía 15 | Estado | Evidencia |
|---|---|---|---|
| 1 | Contraseñas con Argon2id; sin secretos en el repositorio | Cumple | `test_auth_security.py::test_argon2id_hash_verifies_only_the_right_password` y `test_argon2_hashes_are_salted`; `test_auth_api.py::test_register_stores_consent_and_a_hashed_password`. Secretos: el trabajo `secrets` de la CI corre gitleaks 8.21.2 (versión y suma fijas) sobre **todo** el historial en cada *push*; `.env` está en `.gitignore` y solo se versiona `.env.example` sin valores reales |
| 2 | JWT de vida corta, refresco rotatorio, verificación estricta del algoritmo | Cumple | Acceso de 15 min (`ACCESS_TOKEN_TTL_MINUTES`, tope 60). `test_auth_security.py`: `test_expired_access_token_is_rejected`, `test_token_with_another_algorithm_is_rejected`, `test_unsigned_token_is_rejected`, `test_token_without_a_required_claim_is_rejected`, `test_short_secret_is_refused`. Refresco: `test_auth_api.py::test_refresh_rotates_and_detects_reuse` |
| 3 | RBAC en el servidor en todas las rutas `/admin`; sin IDOR | Cumple | **Prueba nueva** `test_route_roles.py`: recorre todas las rutas de la aplicación y exige `require_admin` en cada una bajo `/api/v1/admin` y `require_evaluator` bajo `/api/v1/evaluation` (23 rutas hoy: 18 de administración y 5 de evaluación; una ruta nueva sin rol hace fallar la prueba; se comprobó quitando el rol a propósito: 6 fallos). IDOR: `test_blind_evaluation_api.py::test_evaluator_cannot_reach_admin_or_owner_routes` y `test_submission_of_one_evaluator_is_not_visible_to_another`; `test_reports_api.py::test_owner_and_admin_see_the_photo_and_others_do_not`; `GET /reports/{id}` solo para autor, administradores y quien confirmó (decisión 49) |
| 4 | Consultas 100 % parametrizadas | Cumple | SQLAlchemy con parámetros enlazados; ruff aplica las reglas de flake8-bandit (`S`), y `ruff check app --select S608` (SQL armado con texto) está limpio. La única consulta armada con `f"…"` (`blind_reader.py`, `FOR SHARE`) junta dos constantes del código, sin datos del usuario |
| 5 | CORS restringido, cabeceras de seguridad, HTTPS | Cumple en local · HTTPS configurado, sin desplegar | CORS: `test_middleware.py::test_cors_allows_only_panel_origin`. Cabeceras de la API en el stack local: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`. Panel (nginx): CSP con `default-src 'self'` y `frame-ancestors 'none'`, `nosniff`, `Referrer-Policy: no-referrer`. HSTS solo en producción (`test_hsts_only_in_production`). HTTPS: Caddy con Let's Encrypt y redirección en `infra/docker-compose.prod.yml` (fila 121), sin servidor todavía (D1 de la guía de la prueba piloto) |
| 6 | Límite de solicitudes en login, registro y reportes | Cumple | Login: bloqueo progresivo por correo y 30 por IP cada 5 min (`LOGIN_PER_IP_PER_5_MINUTES`); registro: 30 por IP y hora; reportes: 10 por usuario y 100 por IP por hora; mapa: 60 por usuario y minuto. `test_rate_limit.py::test_auth_routes_are_limited_per_ip`, `test_login_limit_per_ip_is_configurable`, `test_login_lockout.py`. **Nuevo en esta fase:** límite global de 600 solicitudes por IP cada 5 min para cualquier ruta (`test_global_rate_limit.py`, 12 pruebas; fila 140). Limitación conocida: los contadores viven en la memoria de un proceso (ADR 0004) |
| 7 | Fotos: tipo real, tamaño máximo, EXIF eliminado | Cumple | `test_photo_processing.py`: la imagen se recodifica sin EXIF, sin GPS y sin marca del aparato (aserciones sobre `getexif()`), `test_truncated_photo_is_rejected`, `test_photo_with_too_many_pixels_is_rejected_before_decoding`; `test_create_report.py`: tipo no admitido y foto de más de 10 MB rechazados; `test_body_size_limit.py`: 413 por `Content-Length` antes de leer el cuerpo; `test_reports_api.py::test_photo_is_stored_recoded_without_metadata` |
| 8 | Consentimiento Ley 1581; consultar, actualizar y suprimir | Cumple | `test_auth_api.py::test_register_stores_consent_and_a_hashed_password` (fecha y versión de la política); `test_me_api.py`: actualizar nombre y correo con contraseña, `test_data_deletion_anonymizes_the_titular_and_keeps_the_reports`, `test_after_deletion_the_account_is_unusable`, `test_data_deletion_removes_the_photos_and_keeps_the_report`. La app tiene las pantallas de perfil, edición y supresión con constancia (fila 111) |
| 9 | Auditoría de dependencias sin altas ni críticas | Cumple · corregido en esta fase | `pip-audit` (backend, dependencias de producción): «No known vulnerabilities found». `npm audit --audit-level=high` en el panel y la página: «found 0 vulnerabilities». La CI repite las auditorías en cada *push*. **Hallazgo corregido:** Dependabot no vigilaba la app Flutter; ahora sí (`pub` en `/mobile`, fila 141). `flutter pub outdated`: 4 paquetes directos y 23 transitivos con versión más nueva, ninguno con aviso de seguridad conocido; se actualizan cuando Dependabot los proponga y se pruebe la app en el celular |
| 10 | Contenedores sin root; logs sin datos personales | Cumple | En el stack local: la API corre como `uid=999(app)` (`USER app` en `api.Dockerfile`), el panel como `uid=101(nginx)` (imagen `nginx-unprivileged`) y el servidor de PostgreSQL como `postgres` (uid 999). Ambas imágenes propias tienen `HEALTHCHECK`. Logs: **prueba nueva** `test_logging_privacy.py`: el log de cada petición guarda método, ruta, estado y duración, sin la cadena de consulta, la IP ni el token (se comprobó registrando la URL completa a propósito: la prueba falla) |
| 11 | Tokens guardados de forma segura en el móvil y el panel | Cumple | App: `flutter_secure_storage` (Keystore/Keychain) en `secure_token_store.dart`, con `secure_token_store_test.dart`. Panel: el token de acceso vive solo en memoria (`SessionProvider.tsx`) y el refresco en una cookie `HttpOnly` con defensa CSRF (decisión 42): `test_auth_web_api.py::test_web_login_sets_httponly_cookie_and_no_refresh_in_body`, `test_web_login_without_csrf_header_is_403`, `test_web_refresh_requires_csrf`. El único dato en `sessionStorage` es el borrador del orden del evaluador (identificadores de reportes, sin datos personales) |

## Análisis estático

SonarQube Cloud, tras las tareas 1 y 2 de esta fase (filas 138 y 139): **0 avisos abiertos,
0 errores, 0 vulnerabilidades y 0 puntos de seguridad por revisar** (*hotspots*), con la puerta
de calidad aprobada en `main`.

## Hallazgos de esta revisión

1. **Dependabot no vigilaba la app Flutter.** Corregido (fila 141).
2. **No había una prueba que cubriera todas las rutas administrativas a la vez**: cada ruta
   tenía su prueba de «requiere administrador», pero una ruta nueva podía olvidarlo sin que nada
   fallara. Se añadió `test_route_roles.py`.
3. **Nada protegía que el log de peticiones siguiera sin datos personales.** Se añadió
   `test_logging_privacy.py`.

## Fuera de alcance (necesita servidor)

- HTTPS real, HSTS en el proxy y límite de tamaño de las peticiones por trozos: configurados en
  `infra/docker-compose.prod.yml` con Caddy (fila 121), pendientes de la decisión D1.
- Programar `purge-orphan-photos`, respaldos de la base y monitoreo de errores (Sentry,
  decisión 67): se retoman antes de la prueba con otras personas (fila 137).

## Pendientes conocidos

- Los límites de solicitudes cuentan en la memoria de un solo proceso: con varios procesos o
  réplicas cada uno lleva su cuenta (ADR 0004). Suficiente para el MVP.
- El registro revela si un correo ya existe (409), riesgo aceptado en la decisión 30b y acotado
  por el límite de registros por IP.

## Cómo repetir esta revisión

```bash
cd backend && uv export --frozen --no-dev --no-hashes -o /tmp/req.txt && uv run pip-audit -r /tmp/req.txt
cd admin-web && npm audit --audit-level=high
cd landing && npm audit --audit-level=high
cd mobile && flutter pub outdated
cd backend && uv run ruff check app --select S608
infra/scripts/test-integration.sh -q        # incluye test_route_roles y test_logging_privacy
docker compose -f infra/docker-compose.yml --env-file .env up -d --build --wait db api admin-web
curl -sI http://127.0.0.1:8080/  # cabeceras del panel; la API: curl -s -D - -o /dev/null http://127.0.0.1:8000/api/v1/privacy-policy
docker compose -f infra/docker-compose.yml --env-file .env exec -T api id
```
