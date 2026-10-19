# App ciudadana en Flutter — flujo crítico (diseño)

Fecha: 2026-10-19 · Refs: decisión 44, decisión 1 (Riverpod), decisión 47 (pantallas de Figma)
HU: HU-07, HU-10, HU-11, HU-15, HU-16 (y HU-02 en el cliente)

## 1. Intención

La app ciudadana es la primera parte del MVP que se va a **ver funcionando** fuera del backend:
el responsable la va a mostrar en **su propio celular Android**, conectado por USB a su
computador, al asesor y a ciudadanos de prueba. Tiene que demostrar el ciclo completo del
problema de la tesis: un ciudadano reporta un daño con foto y ubicación, el sistema le avisa si
ya existe un reporte a menos de 25 m (para no duplicarlo) y el ciudadano ve después qué pasó con
lo suyo.

**Éxito:** desde un celular Android real, una persona nueva se registra aceptando la política,
toma la foto de un daño en Pasto, elige la severidad, la envía y la ve en «Mis reportes» con su
estado (Evaluado) y su dirección. Si reporta otra vez en el mismo sitio, la app le muestra el
posible duplicado y puede confirmarlo en lugar de crear otro.

## 2. Alcance

### 2.1 Metas (este trabajo)

App (Flutter, Android):

1. Bienvenida.
2. Registro con la **política de datos** (Ley 1581): se muestra la versión vigente
   (`GET /privacy-policy`) y el registro envía `accepted_policy` y `policy_version`.
3. Inicio de sesión, con el estado «Cuenta bloqueada» (429 con `Retry-After`).
4. Permisos de cámara y ubicación, pedidos en contexto con explicación, y la pantalla «Permiso
   denegado» con un acceso a los ajustes del sistema.
5. Nuevo reporte, paso 1 de 2: foto (cámara) y ubicación (GPS del teléfono).
6. Nuevo reporte, paso 2 de 2: severidad (baja, media o alta) y descripción opcional.
7. Antes de enviar se consulta `GET /reports/nearby`. Si hay candidatos, se abre la pantalla
   **Posible duplicado**: «Confirmar este reporte» (HU-16) o «Crear de todos modos»
   (`create_anyway=true`). El 409 `REPORT_DUPLICATE_NEARBY` del envío lleva a la misma pantalla
   (carrera entre la consulta y el envío).
8. Reporte enviado: confirmación con el estado inicial y la dirección.
9. Errores del envío con sus pantallas de Figma: fuera del área de servicio (422), límite
   alcanzado (429), foto rechazada (413, 415 y 422 de foto).
10. Mis reportes: lista con miniatura, dirección, fecha, severidad y chip de estado; estados de
    cargando, vacío y error con reintento (en Figma). Incluye también los reportes **que el
    ciudadano confirmó**, marcados «Lo confirmaste» y sin miniatura.
11. Detalle de un reporte propio: foto, dirección, severidad, estado, historial de estados y
    número de confirmaciones. Detalle de un reporte confirmado: vista limitada (ver 4.3).
12. Tras confirmar un reporte en «Posible duplicado», la app lo dice («Confirmación
    registrada», con los componentes de «Reporte enviado») y lleva a Mis reportes.
13. Cerrar sesión (`POST /auth/logout`) desde un acceso mínimo (ver 2.2).
14. Sesión: access token de 15 min y refresh rotatorio guardados en `flutter_secure_storage`;
    refresco automático ante un 401 y vuelta al inicio de sesión si el refresco falla.

Backend (lo que la app necesita y aún no existe; la decisión 44 lo dejó para «cuando la app lo
pida»):

- **B1. `POST /api/v1/reports/{id}/confirmations`** (HU-16). Ver 4.1.
- **B2. `GET /api/v1/me/reports`**, paginado. Ver 4.2.
- **B3. `GET /api/v1/reports/{id}`**: detalle visto por su autor (o un administrador). Ver 4.3.

### 2.2 Fuera de este trabajo (a propósito)

- Mapa de reportes (pantalla «Mapa de reportes» y «Mapa · Sin conexión»): se hará después del
  flujo crítico; depende del listado público con *bounding box*, que no existe.
- Perfil completo: editar datos, confirmar contraseña, eliminar mis datos y constancia. En esta
  entrega el perfil solo tiene el nombre, el correo, el enlace a la política y **Cerrar sesión**.
  Los endpoints ya existen; las pantallas se construyen en la siguiente entrega de la app.
- Cola de envío persistente en segundo plano (sobrevive a cerrar la app). En esta entrega: si el
  envío falla por red, el borrador (foto, ubicación, severidad, descripción y la misma
  `Idempotency-Key`) se conserva en memoria y el botón «Reintentar» lo reenvía sin duplicar.
- iOS: el proyecto se crea con la plataforma, pero no se compila ni se prueba (no hay Mac).
- HTTPS: llega con HU-17. En desarrollo el celular habla con el backend por HTTP en la red local.
- Panel administrativo.

### 2.3 Anti-metas (sería un fracaso aunque funcione)

- Que la app calcule U, decida transiciones o deduzca duplicados por su cuenta: el cliente solo
  **muestra** lo que dice el servidor (guía 10.4).
- Tokens en `SharedPreferences` o en logs; fotos con EXIF que salgan del teléfono sin que el
  servidor las recodifique (el servidor ya lo hace; el cliente no lo debe impedir).
- Colores, tipografías o espaciados sueltos en los widgets en lugar de los tokens de la 10.1.
- Mostrar a terceros la ubicación exacta o el autor de un reporte ajeno.
- Que un reintento por red cree dos reportes.

## 3. Restricciones

- Stack fijo (guía 3): Flutter; Riverpod (decisión 1); `go_router`; `flutter_secure_storage`.
- Estructura *feature-first* con capas `presentation / application / domain / data` (guía 10.4).
- Tokens visuales de la 10.1 en un `ThemeData` central (colores, Archivo 700/800 para títulos,
  Manrope 400–700 para el cuerpo; fuentes empaquetadas en `assets/fonts`, no descargadas en
  tiempo de ejecución).
- Fidelidad al Figma (`wjbs0QbgIJvRiduvFAimAI`): pantallas originales y las añadidas por la
  decisión 47. Lo que no esté diseñado se resuelve con los componentes existentes y se anota.
- Interfaz en español de Colombia; decimales con coma; fechas en hora de Bogotá, formato corto
  («13 oct»).
- Accesibilidad WCAG 2.2 AA: áreas táctiles ≥ 44 px, `Semantics`, estado nunca solo por color,
  respeto del tamaño de texto del sistema.
- La URL del backend se pasa con `--dart-define=API_BASE_URL=...`; el tráfico HTTP sin cifrar
  solo se permite en la variante *debug* (configuración de seguridad de red de Android).
- Calidad: `flutter analyze` sin avisos, `dart format`, `flutter test` (unitarias y de widgets).
  El backend sigue con ruff, mypy estricto en dominio y aplicación, pytest y cobertura ≥ 80 %.
- Ramas y commits según la guía 8.4: una rama por implementación, *merge* directo a `main`, sin PR.

## 4. Decisiones del backend

### 4.1 B1 · Confirmar un reporte (HU-16)

`POST /api/v1/reports/{id}/confirmations`, sin cuerpo, autenticado.

- 201 con `{ "report_id", "confirmations" }` (total tras confirmar).
- 404 `REPORT_NOT_FOUND` si no existe.
- 409 `CONFIRMATION_ALREADY_EXISTS` si el usuario ya lo confirmó (restricción única
  usuario–reporte que ya está en la tabla `confirmacion`).
- 409 `REPORT_NOT_ACTIVE` si el reporte está Reparado (solo se confirman reportes activos, los
  mismos que muestra `nearby`).
- Las confirmaciones **no cambian U** (guía 2.2); solo se cuentan.
- Límite por usuario, como en `nearby`, para que no sirva para sondear identificadores.
- **Confirmar un reporte propio** está prohibido: 409 `CONFIRMATION_OWN_REPORT` (propuesta 48,
  aprobada; sección 7). Los candidatos de `nearby` y del 409 `REPORT_DUPLICATE_NEARBY` ganan el
  campo `is_mine` (booleano), y la pantalla de duplicado muestra los propios como «Tu reporte»,
  sin botón de confirmar.

### 4.2 B2 · Mis reportes

`GET /api/v1/me/reports?limit=&offset=`: reportes que el usuario **creó o confirmó**, ordenados
por la fecha de su relación con el reporte (creación o confirmación), del más reciente al más
antiguo. `limit` por defecto 20, máximo 50. Respuesta `{ "items": [...], "total", "limit",
"offset" }`. Cada elemento lleva `relation: "own" | "confirmed"`:

- `own`: el `ReportResponse` actual (ubicación exacta) más `confirmations`.
- `confirmed`: vista limitada, igual a la de un candidato de `nearby` (ubicación pública
  redondeada a 4 decimales, sin autor ni descripción) más `status`, `address`, `severity`,
  `confirmations`, `created_at` y `confirmed_at`. Sin `priority_score`.

La miniatura se pide aparte a `/reports/{id}/photo/thumbnail` y solo para `own` (ya restringe al
autor).

### 4.3 B3 · Detalle de un reporte

`GET /api/v1/reports/{id}`: para el autor, los administradores y **quien lo confirmó**; para
cualquier otro, 404
(no 403, para no revelar que existe; mismo criterio que la foto). Devuelve el `ReportResponse`
más `confirmations` e `history`: lista de cambios de estado `{ status, changed_at, note }` del
más antiguo al más reciente. No incluye quién hizo el cambio (el ciudadano no necesita el nombre
del funcionario). Quien solo lo confirmó recibe la vista limitada de 4.2 (`relation:
"confirmed"`) más `history`, sin observaciones (`note` en null: pueden mencionar datos del
autor). El detalle público para terceros queda fuera.

*Decisión del asistente:* el historial incluye **todas** las filas de `historial_estado`,
también el «Registrado» inicial y el paso automático a «Evaluado» (las que tienen `id_usuario`
NULL); la app no distingue autores, solo muestra estado, fecha y observación.

## 5. Decisiones de la app

- **Ubicación:** la del GPS del teléfono en el momento de la foto, con precisión alta. Si la
  precisión es peor que un umbral (constante con nombre, propuesta: 50 m) se pide esperar o
  reintentar. No hay selección manual en el mapa en esta entrega.
- **Foto:** de la cámara (`image_picker`), comprimida en el teléfono a un lado máximo y calidad
  JPEG razonables antes de subir (guía 10.3, red inestable). El servidor sigue validando y
  recodificando.
- **Idempotencia:** cada borrador genera un UUID v4 al pulsar «Enviar» por primera vez y lo
  conserva en los reintentos.
- **Errores:** un único traductor del formato de error de la API (`code`, `message`, `details`)
  a estados de pantalla; los textos de la API ya están en español y se pueden mostrar.
- **Red:** cliente HTTP con interceptor de `Authorization` y de refresco (un solo refresco en
  vuelo aunque fallen varias peticiones a la vez).
- **Pruebas:** repositorios con interfaces y dobles; pruebas unitarias de controladores
  (contenedor de Riverpod) y de widgets de cada pantalla con sus estados.

## 6. Lo que queda al constructor

- Elección de paquetes concretos para HTTP (`dio` o `http`), compresión de imagen, ubicación
  (`geolocator`) y modelos inmutables (`freezed` o clases a mano), siempre que se registren como
  decisión menor en la bitácora.
- Orden de las ramas y división en commits, respetando una rama por implementación (B1, B2, B3,
  cimientos de la app, autenticación, nuevo reporte, mis reportes).
- Cómo levantar el backend para la prueba en el celular (IP de la red local, puerto, CORS no
  aplica a la app) y documentarlo en `mobile/README.md`, incluidos la carga OSM y el caso de
  probar fuera de Pasto: el área ya es configurable con `REPORT_AREA_BBOX` y `OSM_BBOX` (no hay
  que cambiar código; el responsable confirmó que la prueba es **en Pasto**, con la carga OSM hecha).
- CI de Flutter en GitHub Actions (`flutter analyze` y `flutter test`) en un trabajo aparte.

## 7. Propuesta 48 (protocolo 0.3) — aprobada el 2026-10-19

```
Propuesta 48: impedir confirmar un reporte propio
Dónde: código (B1) y pantalla Posible duplicado
Situación actual: las fuentes solo dicen «una confirmación por usuario y reporte»; nearby
  devuelve también los reportes del propio usuario.
Mejora sugerida: responder 409 CONFIRMATION_OWN_REPORT si el autor intenta confirmar su
  reporte, y en la pantalla de duplicado mostrar sus propios reportes como «Tu reporte» sin el
  botón de confirmar.
Justificación: una confirmación es evidencia de un tercero; contarse a uno mismo infla la
  evidencia y el criterio de desempate (guía 7.4, anti-manipulación del ranking).
Impacto: pequeño; un campo `is_mine` en los candidatos de nearby y una regla en B1. No toca U.
Recomendación: aplicar
```

Decisión del responsable: aplicar («haz lo más recomendable», 2026-10-19).
