# App ciudadana Flutter — flujo crítico · plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** App Android en Flutter con la que un ciudadano se registra con la política de datos, reporta un daño con foto, GPS y severidad, resuelve el posible duplicado (confirmar o crear) y sigue sus reportes creados y confirmados.

**Architecture:** *Feature-first* con capas `presentation / application / domain / data` (guía 10.4). Riverpod para estado e inyección (decisión 1), `go_router` para navegación con redirección por sesión, `dio` con un interceptor de sesión (refresco de un solo vuelo). Los servicios del dispositivo (cámara, GPS, compresión, almacenamiento seguro) quedan detrás de interfaces propias para probar sin dispositivo. La app no calcula nada del dominio: muestra lo que responde la API.

**Tech Stack:** Flutter 3.47 (stable, Dart 3), flutter_riverpod, go_router, dio, flutter_secure_storage, image_picker, geolocator, flutter_image_compress, intl, uuid, url_launcher; pruebas con flutter_test y mocktail.

**Spec:** `docs/superpowers/specs/2026-10-19-app-flutter-flujo-critico-design.md` (y el backend ya integrado: `docs/superpowers/plans/2026-10-19-backend-app-flujo-critico.md`).

## Global Constraints

- Carpeta `mobile/`, paquete Dart `street_repo`, id de aplicación `co.edu.ucc.streetrepo`; plataformas android e ios (solo se compila y prueba android).
- URL del backend solo por `--dart-define=API_BASE_URL=http://<ip-lan>:8000`; sin valor por defecto en release.
- HTTP sin cifrar solo en la variante *debug* (`android/app/src/debug/res/xml/network_security_config.xml`); release exige HTTPS (HU-17).
- Tokens solo en `flutter_secure_storage`; nunca en `SharedPreferences`, logs ni mensajes de error.
- Tokens visuales de la guía 10.1 en un único `AppTokens` + `ThemeData`; ningún `Color(0x…)` fuera de `lib/core/theme/`. Archivo 700/800 (títulos) y Manrope 400–700 (cuerpo) empaquetadas en `assets/fonts/` con su licencia OFL.
- Textos en español de Colombia; decimales con coma (`8,70`); fechas en hora de Bogotá (UTC−5) con formato corto `13 oct`; la API usa punto y UTC.
- Accesibilidad WCAG 2.2 AA: áreas táctiles ≥ 44 px, `Semantics` en iconos y chips, el estado nunca solo por color, respetar el tamaño de texto del sistema.
- Fidelidad al Figma `wjbs0QbgIJvRiduvFAimAI` (sesión de solo lectura): antes de cada pantalla, `get_design_context`/`get_screenshot` de su nodo (tabla de nodos abajo), usando la skill `figma:figma-design-to-code`.
- Calidad: `flutter analyze` sin avisos (`flutter_lints` + reglas estrictas de `analysis_options.yaml`), `dart format --set-exit-if-changed .`, `flutter test` verde antes de cada commit.
- Entorno: `JAVA_HOME=C:\Users\areva\dev\jdk-17.0.20.1+1`, Flutter en `C:\Users\areva\dev\flutter\bin`, SDK de Android en `%LOCALAPPDATA%\Android\Sdk` (ya en el PATH del usuario; en una consola nueva están disponibles).
- Ramas y commits según la guía 8.4 (una rama por tarea, `merge` directo a `main`, sin PR, Conventional Commits con `Refs:` y el pie `Co-Authored-By`/`Claude-Session` vigente).

### Nodos del Figma (página `0:1`)

| Pantalla | Nodo | Pantalla | Nodo |
|---|---|---|---|
| Bienvenida | `2:3` | Iniciar sesión | `2:37` |
| Política de datos | `2:66` | Registro | `14:3` |
| Iniciar sesión · Cuenta bloqueada | `14:45` | Permisos de cámara y ubicación | `14:80` |
| Permiso denegado · Ubicación | `14:116` | Nuevo reporte · Foto y ubicación | `4:77` |
| Nuevo reporte · Severidad | `5:2` | Posible duplicado | `5:54` |
| Reporte enviado | `5:102` | Reporte · Fuera del área de servicio | `15:2` |
| Reporte · Límite alcanzado | `15:25` | Nuevo reporte · Foto rechazada | `15:46` |
| Mis reportes | `6:62` | Mis reportes · Cargando / Vacío / Error | `16:244` / `16:295` / `16:327` |
| Detalle del reporte | `6:3` | Perfil y privacidad | `6:141` |

## Review Focus

1. **Sin red a mitad del envío** (4G inestable en Pasto): el borrador (foto, ubicación, severidad, descripción) y su `Idempotency-Key` se conservan, «Reintentar» no crea un segundo reporte y no se pierde lo escrito. Prueba en Task 5.
2. **Access token vencido con varias peticiones a la vez** (lista + miniaturas): un solo `POST /auth/refresh`, las demás esperan y se reintentan; si el refresco falla, se borra la sesión y se vuelve a «Iniciar sesión» sin bucles. Prueba en Task 2.
3. **GPS sin precisión o desactivado** (interiores, ahorro de batería): no se envía una ubicación peor que 50 m; se explica y se ofrece reintentar o abrir ajustes. Prueba en Task 4.
4. **Texto grande del sistema** (escala 2.0): las pantallas del flujo no se desbordan (sin `RenderFlex overflow`) y los botones siguen visibles. Prueba de widget con `textScaler` 2.0 en Tasks 3, 5 y 6.
5. **El ciudadano cambia el borrador tras un fallo de red** y reenvía: se genera una clave nueva (si no, el servidor respondería 422 `IDEMPOTENCY_KEY_REUSED`). Prueba en Task 5.

---

### Task 1: Cimientos del proyecto (tema, formato, componentes, rutas, CI)

**Files:**
- Create: `mobile/` con `flutter create --org co.edu.ucc --project-name street_repo --platforms android,ios mobile` (conservar `mobile/README.md` y reescribirlo).
- Create: `mobile/analysis_options.yaml` (incluye `package:flutter_lints/flutter.yaml`; `strict-casts`, `strict-inference`, `strict-raw-types`; reglas `prefer_const_constructors`, `require_trailing_commas`, `avoid_print`).
- Create: `mobile/lib/main.dart`, `mobile/lib/app.dart` (`StreetRepoApp`: `ProviderScope` + `MaterialApp.router`, locale `es_CO`).
- Create: `mobile/lib/core/config/app_config.dart`, `mobile/lib/core/theme/app_tokens.dart`, `mobile/lib/core/theme/app_theme.dart`, `mobile/lib/core/format/formatters.dart`.
- Create: `mobile/lib/core/widgets/status_chip.dart`, `severity_chip.dart`, `primary_button.dart`, `state_views.dart`.
- Create: `mobile/lib/core/routing/app_router.dart` (rutas con pantallas vacías; se llenan en las tareas siguientes).
- Create: `mobile/assets/fonts/` (Archivo 700/800, Manrope 400/500/600/700 en TTF + `OFL.txt`), declaradas en `pubspec.yaml`.
- Modify: `.github/workflows/ci.yml` (trabajo `mobile`: `subosito/flutter-action` fijado por commit, canal stable 3.47.x; `flutter pub get`, `dart format --set-exit-if-changed .`, `flutter analyze`, `flutter test`; `working-directory: mobile`).
- Test: `mobile/test/core/theme/app_tokens_test.dart`, `mobile/test/core/format/formatters_test.dart`, `mobile/test/core/widgets/chips_test.dart`, `mobile/test/core/widgets/state_views_test.dart`.

**Interfaces:**
- Produces:
  - `class AppConfig { final Uri apiBaseUrl; static AppConfig fromEnvironment(); }` — lee `String.fromEnvironment('API_BASE_URL')`; lanza `StateError('Falta --dart-define=API_BASE_URL')` si está vacío. `final appConfigProvider = Provider<AppConfig>(...)`.
  - `abstract final class AppTokens` con `ink #1B2430`, `paper #F5F3EE`, `amber #F5B800`, `line #E2DED5`, `textSecondary #5B6573`; estados (`registeredFg #5B6573`, chip `#E8EAEE`/`#3D4756`; `evaluatedFg #2B6CB0`, chip `#D9E8F7`/`#1C4E80`; `prioritizedFg #B7791F`, chip `#FDF0C4`/`#7A4E00`; `repairedFg #1F7A5C`, chip `#DDF1E8`/`#14573F`); severidad `low #2B6CB0`, `medium #B45F06`, `high #B42318`; `minTouchTarget = 44.0`.
  - `ThemeData buildAppTheme()`.
  - `enum ReportStatus { registered, evaluated, prioritized, repaired }` con `fromApi(String)` (`registrado`, `evaluado`, `priorizado`, `reparado`) y `label` (`Registrado`…); `enum Severity { low, medium, high }` con `fromApi`/`toApi` (`baja`, `media`, `alta`) y `label` (`Baja`, `Media`, `Alta`). Viven en `mobile/lib/core/domain/report_enums.dart`.
  - `String formatScore(num value)` → `8,70`; `String formatShortDate(DateTime utc)` → `13 oct` en hora de Bogotá; `String formatRelative(DateTime utc, DateTime nowUtc)` → `hoy`, `hace 3 días`, `hace 1 semana`, `hace 3 semanas` (como el Figma de Mis reportes).
  - Widgets: `StatusChip(ReportStatus status)`, `SeverityChip(Severity severity)`, `PrimaryButton({required String label, VoidCallback? onPressed, bool loading = false})` (deshabilitado y con indicador mientras `loading`: evita el doble envío), `LoadingView`, `EmptyView({required String title, String? message, Widget? action})`, `ErrorView({required String message, required VoidCallback onRetry})`.

- [ ] **Step 1: Crear el proyecto, dependencias y fuentes.** `flutter create …`; añadir dependencias con `flutter pub add flutter_riverpod go_router dio flutter_secure_storage image_picker geolocator flutter_image_compress intl uuid url_launcher` y `flutter pub add --dev mocktail`; descargar las TTF de Google Fonts (Archivo, Manrope) con su `OFL.txt`. `flutter test` (el de plantilla) → PASS; luego borrar `test/widget_test.dart` de plantilla.
- [ ] **Step 2: Pruebas que fallan:**
  - `formatters_test.dart`: `formatScore(8.7) == '8,70'`, `formatScore(3.6) == '3,60'`, `formatScore(10) == '10,00'`; `formatShortDate(DateTime.utc(2026, 10, 14, 3)) == '13 oct'` (las 3:00 UTC son el 13 en Bogotá); `formatRelative` con `now = DateTime.utc(2026,10,19,15)`: mismo día → `hoy`, −3 días → `hace 3 días`, −7 → `hace 1 semana`, −21 → `hace 3 semanas`.
  - `app_tokens_test.dart`: `AppTokens.amber == const Color(0xFFF5B800)` y los cuatro colores de chip de estado.
  - `chips_test.dart`: `StatusChip(ReportStatus.prioritized)` muestra el texto `Priorizado` y tiene `Semantics(label: 'Estado: Priorizado')`; `SeverityChip(Severity.high)` muestra `Alta`; `ReportStatus.fromApi('evaluado') == ReportStatus.evaluated`; `fromApi('otro')` lanza `FormatException`.
  - `state_views_test.dart`: `ErrorView` llama a `onRetry` al tocar «Reintentar»; `PrimaryButton(loading: true)` no llama a `onPressed`.
- [ ] **Step 3:** `flutter test` → FAIL (símbolos no definidos).
- [ ] **Step 4: Implementar** tokens, tema, formatos (`intl` con `es_CO`; Bogotá = UTC−5 fijo, Colombia no tiene horario de verano), enums, widgets, `AppConfig`, `app.dart` con `MaterialApp.router` y `app_router.dart` con las rutas de la Task 3/5/6 como `Placeholder`.
- [ ] **Step 5:** `dart format --set-exit-if-changed . && flutter analyze && flutter test` → todo verde. `flutter build apk --debug --dart-define=API_BASE_URL=http://10.0.2.2:8000` → compila.
- [ ] **Step 6:** trabajo `mobile` en la CI; `mobile/README.md` (requisitos, cómo correr pruebas, cómo ejecutar en el celular — se completa en la Task 7). Registrar en `docs/bitacora.md` la **decisión menor** de paquetes de la app (lista del Tech Stack y por qué: sin generación de código; modelos inmutables a mano).
- [ ] **Step 7: Commit** en `feat/mobile-cimientos`: `feat(mobile): crear la app Flutter con tema, formatos y componentes base` con `Refs: HU-07`. Integrar y verificar la CI.

---

### Task 2: Red, errores de la API y sesión

**Files:**
- Create: `mobile/lib/core/network/api_error.dart`, `api_client.dart`, `session_interceptor.dart`
- Create: `mobile/lib/features/auth/domain/session.dart`, `auth_repository.dart`
- Create: `mobile/lib/features/auth/data/token_store.dart`, `secure_token_store.dart`, `auth_api.dart`, `http_auth_repository.dart`
- Create: `mobile/lib/features/auth/application/session_controller.dart`
- Test: `mobile/test/support/fake_http_adapter.dart`, `mobile/test/core/network/api_error_test.dart`, `mobile/test/core/network/session_interceptor_test.dart`, `mobile/test/features/auth/session_controller_test.dart`

**Interfaces:**
- Produces:
  - `sealed class ApiFailure implements Exception` con `ApiError({required int status, required String code, required String message, Map<String, Object?> details, Duration? retryAfter})`, `NetworkFailure()` (sin conexión o tiempo agotado) y `UnexpectedFailure()`. `ApiFailure fromDioException(DioException e)` lee el cuerpo `{code, message, details}` y `Retry-After` (segundos). El `message` del servidor ya está en español y se puede mostrar; para `NetworkFailure` el texto es «No hay conexión. Revisa tu señal e intenta de nuevo.».
  - `abstract interface class TokenStore { Future<AuthTokens?> read(); Future<void> write(AuthTokens tokens); Future<void> clear(); }`; `class AuthTokens { final String access; final String refresh; }`. `SecureTokenStore` con `flutter_secure_storage` (claves `access_token`, `refresh_token`).
  - `Dio buildApiClient(AppConfig config, TokenStore store, Future<AuthTokens> Function(String refresh) refresh, void Function() onSessionExpired)` — `connectTimeout` 10 s, `receiveTimeout` 30 s (fotos), `sendTimeout` 60 s.
  - `SessionInterceptor`: añade `Authorization: Bearer <access>` salvo en `/auth/*`; ante 401 con token, hace **un único** refresco compartido (un `Completer` en vuelo), guarda los tokens nuevos y reintenta una vez; si el refresco falla (401 `INVALID_REFRESH_TOKEN` o cualquier error), `store.clear()` y `onSessionExpired()`. Nunca reintenta en bucle.
  - `abstract interface class AuthRepository { Future<PrivacyPolicy> privacyPolicy(); Future<void> register({required String name, required String email, required String password, required String policyVersion}); Future<void> login({required String email, required String password}); Future<void> logout(); Future<UserProfile> me(); }`. `register` envía `accepted_policy: true`; tras registrar, la app hace `login` (el registro no devuelve tokens).
  - `class PrivacyPolicy { final String version; final Uri? url; }`, `class UserProfile { final String id, name, email, role; }`.
  - `sealed class SessionState`: `SessionUnknown`, `SignedOut`, `SignedIn(UserProfile user)`. `final sessionControllerProvider = AsyncNotifierProvider<SessionController, SessionState>`; `SessionController` con `restore()` (lee tokens y llama a `me`), `signIn(email, password)`, `register(...)`, `signOut()` (llama a logout aunque falle la red y siempre borra tokens).

- [ ] **Step 1: Pruebas que fallan** (con `FakeHttpAdapter`, un `HttpClientAdapter` que responde según método y ruta y cuenta llamadas):
  - `api_error_test.dart`: un 409 con `{"code":"EMAIL_ALREADY_REGISTERED","message":"…","details":{}}` → `ApiError(status: 409, code: 'EMAIL_ALREADY_REGISTERED')`; un 429 con `Retry-After: 120` → `retryAfter == Duration(seconds: 120)`; un `DioExceptionType.connectionError` → `NetworkFailure`.
  - `session_interceptor_test.dart`: `test_adds_bearer_except_on_auth_routes`; `test_three_parallel_401_trigger_one_refresh` (tres GET simultáneos con token vencido → `refreshCalls == 1`, las tres responden 200); `test_failed_refresh_clears_tokens_and_expires_session_once` (`store.clear` llamado, `onSessionExpired` llamado 1 vez, sin más peticiones).
  - `session_controller_test.dart`: `restore` sin tokens → `SignedOut`; con tokens y `me` OK → `SignedIn`; `signOut` con red caída → igual queda `SignedOut` y tokens borrados.
- [ ] **Step 2:** `flutter test test/core/network test/features/auth` → FAIL.
- [ ] **Step 3: Implementar** según las interfaces.
- [ ] **Step 4:** las pruebas → PASS; `flutter analyze` limpio.
- [ ] **Step 5: Commit** en `feat/mobile-red-y-sesion`: `feat(mobile): cliente HTTP con errores uniformes y sesión con refresco` con `Refs: HU-10`. Integrar.

---

### Task 3: Bienvenida, registro con política e inicio de sesión

**Files:**
- Create: `mobile/lib/features/auth/presentation/welcome_screen.dart`, `register_screen.dart`, `privacy_policy_screen.dart`, `login_screen.dart`
- Create: `mobile/lib/features/auth/application/register_controller.dart`, `login_controller.dart`
- Modify: `mobile/lib/core/routing/app_router.dart` (redirección por sesión)
- Test: `mobile/test/features/auth/presentation/*_test.dart`, `mobile/test/core/routing/app_router_test.dart`

**Interfaces:**
- Consumes: `AuthRepository`, `sessionControllerProvider`, `ApiFailure` (Task 2); widgets y formatos (Task 1).
- Produces: rutas `/bienvenida`, `/registro`, `/politica`, `/ingresar`, `/mis-reportes` (inicio tras ingresar), `/reportar`, `/perfil`, `/reportes/:id`. Redirección: `SessionUnknown` → pantalla de carga; `SignedOut` fuera de las rutas públicas → `/bienvenida`; `SignedIn` en una ruta pública → `/mis-reportes`; `onSessionExpired` → `/ingresar` con el mensaje «Tu sesión terminó. Ingresa de nuevo.».
- Reglas de pantalla (de la API y la guía):
  - Registro (`14:3`): nombre, correo, contraseña; casilla «Acepto la política de tratamiento de datos (versión X)» con enlace a `/politica`. El botón queda deshabilitado sin la casilla. Errores: `EMAIL_ALREADY_REGISTERED` y `WEAK_PASSWORD` junto al campo; `POLICY_VERSION_OUTDATED` → recarga la política y pide aceptar de nuevo. Lo escrito se conserva ante cualquier error.
  - Política (`2:66`): muestra la versión de `GET /privacy-policy`; si `url` existe, «Leer la política completa» abre el navegador (`url_launcher`); si es null (dev), lo dice.
  - Inicio de sesión (`2:37`): `INVALID_CREDENTIALS` → «Correo o contraseña incorrectos.»; `TOO_MANY_LOGIN_ATTEMPTS` (429) → variante «Cuenta bloqueada» (`14:45`) con la cuenta regresiva de `retryAfter` y el botón deshabilitado hasta que termine.

- [ ] **Step 1: Pruebas de widget que fallan:** registro deshabilitado sin aceptar la política; `EMAIL_ALREADY_REGISTERED` muestra el mensaje bajo el correo y conserva los tres campos; registro correcto llama a `register` con `policyVersion` de la política cargada y luego a `login`; login con 429 `retryAfter: 90 s` muestra «Intenta de nuevo en 1:30» y botón deshabilitado; `app_router_test`: `SignedOut` en `/mis-reportes` redirige a `/bienvenida`, `SignedIn` en `/ingresar` redirige a `/mis-reportes`; Registro e Iniciar sesión con `textScaler: TextScaler.linear(2.0)` sin excepciones de desbordamiento (Review Focus 4).
- [ ] **Step 2:** FAIL → **Step 3:** implementar siguiendo el Figma de cada nodo → **Step 4:** PASS, `flutter analyze` limpio.
- [ ] **Step 5: Commit** en `feat/mobile-acceso`: `feat(mobile): bienvenida, registro con política de datos e inicio de sesión` con `Refs: HU-10, HU-11`. Integrar.

---

### Task 4: Permisos y paso 1 · foto y ubicación

**Files:**
- Create: `mobile/lib/features/report_new/domain/report_draft.dart`, `device_services.dart`
- Create: `mobile/lib/features/report_new/data/geolocator_location_service.dart`, `picker_photo_service.dart`
- Create: `mobile/lib/features/report_new/application/report_draft_controller.dart`
- Create: `mobile/lib/features/report_new/presentation/permissions_screen.dart`, `permission_denied_screen.dart`, `photo_location_screen.dart`
- Create: `mobile/android/app/src/main/AndroidManifest.xml` (permisos `CAMERA`, `ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`, `INTERNET`)
- Test: `mobile/test/features/report_new/report_draft_controller_test.dart`, `mobile/test/features/report_new/presentation/photo_location_screen_test.dart`

**Interfaces:**
- Produces:
  - `const double maxLocationAccuracyMeters = 50;` `const int maxPhotoSidePx = 1600;` `const int photoJpegQuality = 85;` (en `report_draft.dart`).
  - `class GeoFix { final double latitude, longitude, accuracyMeters; }`; `class CapturedPhoto { final Uint8List jpegBytes; }`.
  - `abstract interface class LocationService { Future<LocationPermissionState> permission(); Future<LocationPermissionState> request(); Future<GeoFix> currentFix(); Future<void> openSettings(); }` con `enum LocationPermissionState { granted, denied, deniedForever, serviceDisabled }`.
  - `abstract interface class PhotoService { Future<CapturedPhoto?> takePhoto(); }` — cámara trasera; comprime a `maxPhotoSidePx` y `photoJpegQuality` con `flutter_image_compress`; `null` si el ciudadano cancela.
  - `class ReportDraft { final CapturedPhoto? photo; final GeoFix? fix; final Severity? severity; final String description; final String? idempotencyKey; ReportDraft copyWith(...); }` — **cualquier cambio de foto, ubicación, severidad o descripción pone `idempotencyKey` en null** (Review Focus 5).
  - `final reportDraftProvider = NotifierProvider<ReportDraftController, ReportDraft>`; métodos `capturePhoto()`, `locate()` (lanza o expone `LocationTooImprecise(accuracy)` si `accuracy > 50`), `setSeverity`, `setDescription`, `reset()`.
- Pantallas: Permisos (`14:80`) se muestra antes de la primera captura con la explicación de por qué se piden cámara y ubicación; si la ubicación queda `deniedForever` o el GPS apagado → Permiso denegado (`14:116`) con «Abrir ajustes». Paso 1 (`4:77`): vista de la foto, la precisión «±12 m» y «Siguiente» habilitado solo con foto y ubicación válida.

- [ ] **Step 1: Pruebas que fallan** (con `FakeLocationService` y `FakePhotoService`): `locate` con `accuracy 72 m` → estado `LocationTooImprecise` y «Siguiente» deshabilitado con el texto «La ubicación aún no es precisa (±72 m). Espera unos segundos o sal a un lugar abierto.» y botón «Reintentar» (Review Focus 3); `serviceDisabled` → navega a Permiso denegado; `copyWith(severity: …)` sobre un borrador con clave → `idempotencyKey == null`; cancelar la cámara no borra la foto anterior.
- [ ] **Step 2:** FAIL → **Step 3:** implementar (adaptadores reales con `geolocator` `LocationAccuracy.high`, límite 15 s) → **Step 4:** PASS.
- [ ] **Step 5: Commit** en `feat/mobile-captura`: `feat(mobile): permisos y captura de foto y ubicación` con `Refs: HU-02, HU-07`. Integrar.

---

### Task 5: Paso 2, posible duplicado, envío y sus errores

**Files:**
- Create: `mobile/lib/features/report_new/domain/new_report_repository.dart`, `nearby_report.dart`, `submit_outcome.dart`
- Create: `mobile/lib/features/report_new/data/http_new_report_repository.dart`
- Create: `mobile/lib/features/report_new/application/submit_report_controller.dart`
- Create: `mobile/lib/features/report_new/presentation/severity_screen.dart`, `duplicate_screen.dart`, `report_sent_screen.dart`, `report_error_screen.dart`
- Test: `mobile/test/features/report_new/submit_report_controller_test.dart`, `mobile/test/features/report_new/presentation/duplicate_screen_test.dart`, `severity_screen_test.dart`

**Interfaces:**
- Consumes: `ReportDraft`, `reportDraftProvider` (Task 4); `ApiFailure` (Task 2).
- Produces:
  - `class NearbyReport { final String id; final double distanceMeters; final ReportStatus status; final Severity severity; final int confirmations; final String address; final DateTime createdAt; final bool isMine; }` (de `GET /reports/nearby` y de `details.items` del 409).
  - `abstract interface class NewReportRepository { Future<List<NearbyReport>> nearby(GeoFix fix); Future<CreatedReport> create(ReportDraft draft, {required String idempotencyKey, required bool createAnyway}); Future<int> confirm(String reportId); }` — `create` envía multipart (`photo` como `foto.jpg` `image/jpeg`, `longitude`, `latitude`, `severity` con `toApi`, `description` si no está vacía, `create_anyway`) y la cabecera `Idempotency-Key`; 201 y 200 son éxito. `CreatedReport { final String id; final ReportStatus status; final String address; }`.
  - `sealed class SubmitOutcome`: `Sent(CreatedReport)`, `Confirmed(int confirmations)`, `PossibleDuplicates(List<NearbyReport>)`, `OutsideServiceArea`, `RateLimited(Duration retryAfter)`, `PhotoRejected(String message)`, `SubmitFailed(String message, {required bool retryable})`.
  - `SubmitReportController` (`AsyncNotifier`): `checkAndSubmit()` → `nearby`; si hay candidatos → `PossibleDuplicates` (no envía); si no → `create(createAnyway: false)`. `createAnyway()` → `create(createAnyway: true)`. `confirm(id)` → `Confirmed`. La clave: si `draft.idempotencyKey` es null se genera un UUID v4 y se guarda en el borrador **antes** de enviar; los reintentos reutilizan la misma.
  - Mapeo de errores: 409 `REPORT_DUPLICATE_NEARBY` → `PossibleDuplicates(details.items)`; 422 `LOCATION_OUTSIDE_SERVICE_AREA` → `OutsideServiceArea` (`15:2`); 429 `REPORT_RATE_LIMITED` → `RateLimited` (`15:25`); 413 `PHOTO_TOO_LARGE`, 415 `PHOTO_UNSUPPORTED_TYPE`, 422 `PHOTO_INVALID` → `PhotoRejected` (`15:46`, vuelve al paso 1); `NetworkFailure` → `SubmitFailed(retryable: true)`; 409 `CONFIRMATION_ALREADY_EXISTS` → `Confirmed` con el total que ya tiene (se considera hecho); `CONFIRMATION_OWN_REPORT` no debería ocurrir (la UI no ofrece confirmar los propios) → `SubmitFailed(retryable: false)`; cualquier otro → `SubmitFailed(message del servidor, retryable: false)`.
- Pantallas: Severidad (`5:2`, «Paso 2 de 2», tres opciones con su color y texto, descripción opcional de hasta 500 caracteres con contador). Posible duplicado (`5:54`): lista con distancia («a 12 m»), estado, severidad, confirmaciones y dirección; los `isMine` llevan «Tu reporte» y **sin** botón de confirmar; acciones «Confirmar este reporte» y «Crear de todos modos». Reporte enviado (`5:102`): estado inicial y dirección; la misma pantalla con el título «Confirmación registrada» tras confirmar. Tras éxito: `reset()` del borrador e ir a `/mis-reportes`.

- [ ] **Step 1: Pruebas que fallan:**
  - `test_network_failure_keeps_the_draft_and_retry_reuses_the_key` (Review Focus 1): primer `create` lanza `NetworkFailure`, el borrador sigue completo, el segundo `create` recibe la **misma** clave y responde 201 → `Sent`; el repositorio recibió 2 llamadas con la misma clave.
  - `test_changing_severity_after_a_failure_uses_a_new_key` (Review Focus 5).
  - `test_nearby_candidates_stop_the_submission`; `test_409_duplicate_race_shows_the_candidates`; `test_create_anyway_sends_create_anyway_true`; `test_confirm_already_confirmed_counts_as_done`; un caso por cada error mapeado arriba.
  - `duplicate_screen_test`: el candidato `isMine` muestra «Tu reporte» y no tiene «Confirmar este reporte»; el ajeno sí; `PrimaryButton` en carga impide el doble toque (una sola llamada a `confirm`); con `textScaler` 2.0 sin desbordamiento.
  - `severity_screen_test`: «Enviar» deshabilitado sin severidad; contador `0/500`.
- [ ] **Step 2:** FAIL → **Step 3:** implementar → **Step 4:** PASS.
- [ ] **Step 5: Commit** en `feat/mobile-envio-y-duplicado`: `feat(mobile): severidad, posible duplicado y envío del reporte` con `Refs: HU-07, HU-15, HU-16`. Integrar.

---

### Task 6: Mis reportes, detalle y perfil mínimo

**Files:**
- Create: `mobile/lib/features/my_reports/domain/my_report.dart`, `report_detail.dart`, `my_reports_repository.dart`
- Create: `mobile/lib/features/my_reports/data/http_my_reports_repository.dart`
- Create: `mobile/lib/features/my_reports/application/my_reports_controller.dart`, `report_detail_controller.dart`
- Create: `mobile/lib/features/my_reports/presentation/my_reports_screen.dart`, `report_detail_screen.dart`, `report_thumbnail.dart`
- Create: `mobile/lib/features/profile/presentation/profile_screen.dart`
- Create: `mobile/lib/core/widgets/app_shell.dart` (barra inferior)
- Test: `mobile/test/features/my_reports/*_test.dart`, `mobile/test/features/profile/profile_screen_test.dart`

**Interfaces:**
- Consumes: `ApiFailure`, `buildApiClient` (Task 2); `StatusChip`, `SeverityChip`, `formatRelative`, `formatShortDate`, `formatScore`, `LoadingView`/`EmptyView`/`ErrorView` (Task 1); `sessionControllerProvider` (Task 2).
- Produces:
  - `sealed class MyReport` con `OwnReport` (`id, status, severity, description, address, priorityScore?, needsRoadReview, confirmations, createdAt`) y `ConfirmedReport` (`id, status, severity, address, confirmations, createdAt, confirmedAt`), según `relation` `own`/`confirmed`. `class MyReportsPage { final List<MyReport> items; final int total, limit, offset; bool get hasMore => offset + items.length < total; }`.
  - `class ReportDetail { final String relation; /* own | staff | confirmed */ final MyReport report; final List<HistoryEntry> history; bool get isMine => relation == 'own'; }`; `class HistoryEntry { final ReportStatus status; final DateTime changedAt; final String? note; }`.
  - `abstract interface class MyReportsRepository { Future<MyReportsPage> page({required int offset, int limit = 20}); Future<ReportDetail> detail(String id); Uri thumbnailUrl(String id); }`.
  - `MyReportsController`: carga la primera página, `loadMore()` al llegar al final, `refresh()` (deslizar hacia abajo); filtro local `enum MyReportsFilter { all, inProgress, repaired }` (En proceso = todo estado salvo reparado) sobre lo cargado.
  - `ReportThumbnail(String reportId)`: `Image.network(thumbnailUrl, headers: {'Authorization': 'Bearer …'})` solo para `OwnReport`; los confirmados y los errores muestran el icono de cámara del Figma; nunca se guarda la imagen en caché de disco (la API manda `no-store`).
  - `AppShell`: pestañas **Reportar · Mis reportes · Perfil** (la pestaña Mapa del Figma se omite en esta entrega: el mapa está fuera del alcance, spec 2.2). «Reportar» abre el flujo de las Tasks 4–5.
- Pantallas: Mis reportes (`6:62`) con chips de filtro, tarjetas (miniatura, estado, «hace 3 días», descripción o «Lo confirmaste» para los confirmados, dirección); estados Cargando (`16:244`, esqueletos), Vacío (`16:295`, con «Reportar un daño») y Error (`16:327`, con «Reintentar»). Detalle (`6:3`): foto (solo `own`/`staff`), estado, severidad, dirección, urgencia con coma y chip «Revisar vía» si `needsRoadReview` (solo `own`/`staff`), confirmaciones e historial con fecha corta y observación si existe. Perfil (`6:141`, versión mínima): nombre, correo, versión de la política aceptada, enlace a la política y «Cerrar sesión»; los demás elementos del Figma (editar datos, eliminar mis datos) no se muestran en esta entrega.

- [ ] **Step 1: Pruebas que fallan:** parseo de `own`, `confirmed` y `staff` desde JSON de ejemplo copiado de la API; `hasMore` falso con `offset 0, items 2, total 2`; `loadMore` pide `offset 20` tras una primera página de 20; filtro «Reparados» deja solo los `repaired`; la lista vacía muestra el `EmptyView` del Figma; un `NetworkFailure` muestra `ErrorView` y «Reintentar» vuelve a cargar; la tarjeta confirmada muestra «Lo confirmaste» y no pide miniatura; el detalle `confirmed` no muestra foto, urgencia ni observaciones; `formatScore` en el detalle (`8,70`); «Cerrar sesión» llama a `signOut` y vuelve a `/bienvenida`; Mis reportes y Detalle con `textScaler` 2.0 sin desbordamiento.
- [ ] **Step 2:** FAIL → **Step 3:** implementar → **Step 4:** PASS.
- [ ] **Step 5: Commit** en `feat/mobile-mis-reportes`: `feat(mobile): mis reportes, detalle y perfil mínimo` con `Refs: HU-07, HU-12, HU-16`. Integrar.

---

### Task 7: Prueba en el celular del responsable y cierre

**Files:**
- Create: `mobile/android/app/src/debug/res/xml/network_security_config.xml` (tráfico sin cifrar permitido solo en debug) y su referencia en `mobile/android/app/src/debug/AndroidManifest.xml`.
- Modify: `mobile/README.md`, `README.md` (sección App), `CHANGELOG.md`, `docs/bitacora.md` (decisión 49: app aplicada), `AGENTS.md` (sección 13, Estado).
- Test: `mobile/test/app_smoke_test.dart`.

**Interfaces:**
- Consumes: todo lo anterior.

- [ ] **Step 1: Prueba que falla:** `app_smoke_test.dart` — `StreetRepoApp` con repositorios falsos arranca en Bienvenida sin sesión y en Mis reportes con sesión.
- [ ] **Step 2:** FAIL (si ya pasa, revisar que la prueba ejerce la redirección real) → **Step 3:** ajustar → **Step 4:** PASS; `flutter test` completo verde.
- [ ] **Step 5: Backend para el celular:** `docker compose -f infra/docker-compose.yml --env-file .env up -d --build`; carga OSM de Pasto si la base no la tiene (`docker compose … run --rm api python -m app.cli osm-import`); la API escucha en `0.0.0.0:8000` dentro del contenedor y Compose la publica en `127.0.0.1` — para el celular publicar en la IP de la red local con `API_PORT` y una variable de enlace documentada (añadir `API_BIND_ADDRESS`, por defecto `127.0.0.1`, al `ports` del servicio `api` y a `.env.example`) y abrir el puerto 8000 en el firewall de Windows para la red privada.
- [ ] **Step 6: En el celular:** `adb devices` muestra el equipo como `device`; `flutter run --debug --dart-define=API_BASE_URL=http://<ip-lan>:8000`. Recorrer y anotar en `mobile/README.md` (lista de verificación manual): registro con política → ingresar → permisos → foto y ubicación en Pasto → severidad → enviado → aparece en Mis reportes como «Evaluado» con dirección → reportar otra vez en el mismo lugar → Posible duplicado con «Tu reporte» → con una segunda cuenta, confirmar → la segunda cuenta lo ve en Mis reportes con «Lo confirmaste» → modo avión durante un envío → «Reintentar» sin duplicar → cerrar sesión.
- [ ] **Step 7:** documentación listada; `CHANGELOG` («Sin publicar»: app ciudadana con el flujo crítico).
- [ ] **Step 8: Commit** en `feat/mobile-prueba-en-dispositivo`: `feat(mobile): ejecutar en el celular contra el backend local` con `Refs: HU-07, HU-17`. Integrar y verificar la CI.
