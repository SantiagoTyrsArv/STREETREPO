# Panel administrativo para el objetivo 3 (diseño)

Fecha: 2026-11-08 · Refs: decisión 44, fase 6 de `AGENTS.md`, sección 4.3 de la tesis
HU: HU-08, HU-10 (web), HU-12, HU-14 (y los pendientes de la fase 3: rutas de pesos y 409)
Aplica: decisión 42 y ADR 0004 («Panel administrativo en sitio propio»)

## 1. Intención

El responsable necesita **cerrar el resultado del objetivo específico 3** de la tesis
(«Desarrollar los componentes de software del sistema —aplicación móvil ciudadana, panel de gestión
administrativa y base de datos georreferenciada—…»). Hoy la sección 4.3 del documento solo muestra
maquetas de Figma y dice que el código «se reportará en la siguiente fase». La app y la base ya
funcionan; falta el **panel de gestión administrativa**.

El panel está pensado para que lo use **un funcionario de la Secretaría de Infraestructura y
Valorización de Pasto**: entra, ve qué daños atender primero y por qué, y lleva el seguimiento de
cada uno. En lo inmediato, el responsable lo usará para:

- tomar **capturas de pantalla** de cada pantalla y describirlas en la sección 4.3, y
- **mostrarlo funcionando en su propio computador** (asesor y, más adelante, la sustentación).

**Éxito:** en el computador del responsable, `docker compose up` levanta API, base y panel; el
responsable entra con una cuenta de administrador, ve el ranking priorizado con S, F, P y U junto al
mapa de calor, abre un reporte, ve su foto y el desglose del cálculo, lo pasa a «Priorizado» con una
observación que queda en el historial, cambia los pesos del modelo y ve el ranking recalculado con la
nueva versión. Cada pantalla se ve completa y con datos suficientes para una captura útil.

## 2. Alcance

### 2.1 Metas

1. **Inicio de sesión de funcionarios** (pantalla de Figma «inicio de sesión de funcionarios»):
   solo entran cuentas con rol `administrador`. Una cuenta de ciudadano recibe un mensaje claro y no
   entra. Cerrar sesión.
2. **Priorización** (Figma «Priorización»): encabezado con indicadores **Activos · Evaluados ·
   Priorizados · Reparados** (decisión del responsable, sección 9), **mapa de calor** de reportes (HU-08) y **ranking priorizado**
   con S, F, P, U, estado, confirmaciones y el chip **«Revisar vía»**. Paginado. Estados de carga,
   vacío y error (Figma «Panel · Priorización · Estados»).
3. **Detalle y estado** (Figma «Detalle y estado»): foto, ubicación en el mapa, vía de OSM
   (nombre y `highway`) o «Sin vía asociada», servicio crítico más cercano y su distancia,
   **desglose del cálculo** (S, F, P, pesos de la versión usada, U), confirmaciones, **cambio de
   estado con observación** y **historial** completo (con observaciones y quién hizo cada cambio)
   (HU-12).
4. **Pesos del modelo** (Figma «Pesos del modelo»): controles para w₁, w₂ y w₃, validación
   Σ = 1,00 en vivo (y en el servidor), reglas de normalización en solo lectura, guardar con
   recálculo de los reportes activos y **lista de versiones** de configuración (HU-14).
5. **Backend** que estas pantallas necesitan (sección 5), con el RBAC en el servidor.
6. **Datos de demostración** claramente marcados, para que las capturas y la demostración no se
   vean vacías (sección 7).
7. `docker compose up` levanta también el panel (sección 6).

### 2.2 No metas (por ahora)

- Todo lo del **objetivo 4**: zonas o sectores, ficha de evaluación comparativa, vista a ciegas
  para el panel de referencia, exportaciones e indicadores de deduplicación por zona (HU-09).
  Se diseñan aparte cuando el responsable aborde la prueba piloto.
- La pantalla **Datos OSM** (HU-13 ya funciona por línea de comandos: `python -m app.cli osm-import`).
- **Despliegue en internet con HTTPS** (HU-17, decisión 66). El panel corre en el equipo del
  responsable.
- Gestión de cuentas de administrador desde el panel (se siguen creando con `create-admin`).
- Notificaciones, exportar a Excel o PDF, edición de los datos del reporte.

### 2.3 Anti-metas (sería un fracaso aunque funcione)

- Que el panel **calcule** algo del dominio (U, transiciones válidas, orden del ranking): el cliente
  muestra lo que responde la API (guía 10.4).
- Que los **datos de demostración** puedan confundirse con datos de campo o terminen presentados como
  resultados de la tesis (guía 0.2 y 16).
- Que una ruta `/admin/*` dependa de que la interfaz oculte botones: todo se verifica en el servidor.
- Que el token de sesión quede en `localStorage` (guía 7.3) o que se aparte de la decisión 42.
- Que el panel se aleje del Figma sin pasar por el protocolo 0.3.

## 3. Restricciones

- Stack fijo (guía 3): **React + Leaflet**, TypeScript en modo `strict`; la API es la FastAPI
  existente. Interfaz en español de Colombia, decimales con coma (`8,70`), fechas en hora de Bogotá
  con formato corto («13 oct»).
- Tokens visuales de la guía 10.1 centralizados (variables CSS / objeto de tema), tipografías
  Archivo y Manrope, chips de estado y severidad con texto (no solo color).
- Accesibilidad WCAG 2.2 AA, navegable por teclado, responsivo desde ~1024 px (guía 10.3).
- Mapas con **atribución de OpenStreetMap** y proveedor de *tiles* configurable por variable de
  entorno (guía 3.1).
- Reglas de la sección 2 de la guía: orden del ranking = `priority/domain/ranking.py` (U desc →
  severidad → confirmaciones → antigüedad); la consulta SQL del ranking **debe reproducirlo** (guía
  2.2). Pesos con dos decimales exactos que sumen 1,00; máquina de estados de la guía 2.4
  (Registrado → Evaluado solo por el sistema; avances con salto permitidos, retrocesos prohibidos;
  Reparado es final).
- Privacidad (guía 7.2 y 10.3): el nombre del reportante **solo** aparece en el panel; nada de datos
  personales en logs.
- Proceso (guía 8.3, 8.4 y 13): una rama por funcionalidad, pruebas en cada una, *merge* directo a
  `main` sin PR, Conventional Commits, CHANGELOG y etiqueta `v0.6.0` al cerrar la fase.

## 4. Decisiones de cómo se construye

El responsable dejó estas decisiones técnicas al asistente; se registran en la bitácora como
**decisiones menores** al empezar la implementación.

| Tema | Decisión | Motivo |
|---|---|---|
| Proyecto | `admin-web/` con **Vite + React 18 + TypeScript strict** | Estándar actual para una SPA; arranque y compilación rápidos |
| Datos del servidor | **TanStack Query** | Lo recomienda la guía 10.4; caché, reintentos e invalidación tras mutaciones |
| Rutas | **React Router** con rutas protegidas por rol | Rutas protegidas (guía 10.4) |
| Cliente HTTP | `fetch` envuelto en un módulo `api/` propio, con tipos **generados desde el OpenAPI** de la API (`openapi-typescript`) | La guía pide un cliente aislado y, cuando se pueda, generado del contrato |
| Mapa | **react-leaflet** + **leaflet.heat** para el mapa de calor; marcadores con **leaflet.markercluster** en el detalle y como capa opcional | Plugin de calor que pide la guía 3; *clustering* (guía 10.3) |
| Sesión | Según la **decisión 42 y el ADR 0004** (aprobados): token de acceso **en memoria**; token de refresco en **cookie `HttpOnly`, `Secure`, `SameSite=Strict`**, con `Path` limitado a las rutas de autenticación, **cabecera anti-CSRF** y comprobación de `Origin`. Al recargar la página, el panel recupera la sesión con la cookie | Decisión ya aprobada para esta fase; requiere la variante web de `/auth/login`, `/auth/refresh` y `/auth/logout` (sección 5) |
| Servir el panel | Contenedor **nginx** que sirve el panel compilado en **su propio origen** (en local, `http://localhost:<ADMIN_WEB_PORT>`), contra la API en el suyo; **CORS con el origen exacto del panel y credenciales**, nunca `*` (decisión 42) | Un solo `docker compose up`; cabeceras de seguridad (CSP, `X-Content-Type-Options`, `Referrer-Policy`, `noindex`) en nginx. Los navegadores tratan `localhost` como contexto seguro, así que la cookie `Secure` funciona en local sin HTTPS |
| Pruebas | **Vitest + Testing Library** (componentes y lógica), **MSW** para simular la API, **Playwright** para 2–3 flujos de punta a punta | Herramientas de la guía 8.2 |
| Calidad | `eslint` + `prettier`, `tsc --noEmit`, `npm audit` en la CI | Guía 8.2 y 7.3 |

## 5. Backend necesario

Todas las rutas nuevas van bajo `/api/v1/admin/` y exigen `require_admin` (ya existe). Cada una sigue
las capas de la guía 4.2 (router → caso de uso → dominio ← repositorio), con pruebas unitarias e
integración contra PostGIS.

1. **`GET /admin/ranking`**: reportes con estado, S, F, P, U, confirmaciones, «Revisar vía»
   (`id_via` NULL), nombre de la vía, fecha y miniatura. Paginación `limit/offset` con tope; filtro
   opcional por estado (por defecto, los activos: todo salvo Reparado). Orden en SQL idéntico a
   `ranking.py`, con una prueba que compare ambos.
2. **`GET /admin/summary`**: los cuatro indicadores del encabezado: activos (todo salvo Reparado),
   evaluados, priorizados y reparados. Conteos por estado; ninguna regla nueva.
3. **`GET /admin/heatmap`**: puntos (lat, lon, U) de los reportes activos, con *bounding box*
   opcional. Coordenadas exactas: es una ruta de administrador.
4. **`GET /admin/reports/{id}`**: detalle completo para el administrador: lo que ya da
   `FullReportView` más la vía (nombre, `highway`), el servicio crítico más cercano y su distancia,
   la evaluación vigente con los pesos de su versión, el nombre del reportante y el historial con
   observaciones y autor del cambio. Puede reutilizar `GET /reports/{id}` si se extiende sin
   romper la app.
5. **`PATCH /admin/reports/{id}/status`**: cuerpo `{status, note}`; aplica la máquina de estados
   existente (`status_machine.py`) y registra el historial con el administrador. 409 con código
   estable si la transición no es válida.
6. **`GET /admin/weights`** (vigente), **`PUT /admin/weights`** y **`GET /admin/weights/versions`**:
   envuelven el caso de uso `UpdateWeights` que ya existe. El `PUT` lleva la versión sobre la que se
   editó (`base_version_id`); si ya no es la vigente responde **409** (`WEIGHTS_VERSION_CONFLICT`),
   que es el pendiente de la fase 3 para dos administradores guardando a la vez. La respuesta indica
   cuántos reportes se recalcularon.

7. **Variante web de la autenticación** (decisión 42, ADR 0004): `login`, `refresh` y `logout` para el panel entregan y rotan el refresco en la cookie descrita en la sección 4 (el cuerpo no lo lleva), exigen la cabecera anti-CSRF y comprueban `Origin`. La variante de la app móvil (tokens en el cuerpo) no cambia. Al iniciar sesión desde el panel, una cuenta que no es administrador recibe 403 y no se emite sesión. El ADR 0004 se completa con el flujo web.

Las fotos ya se sirven a los administradores (`/reports/{id}/photo` y `/thumbnail`); como `<img>` no envía la cabecera `Authorization`, el panel las pide con el cliente HTTP y las muestra como *blob*.

## 6. Arranque y operación

- `infra/docker-compose.yml` gana el servicio `admin-web` (nginx) publicado solo en `127.0.0.1`,
  con el puerto en `.env` (`ADMIN_WEB_PORT`, documentado en `.env.example`) y `CORS_ORIGINS` de la
  API apuntando a ese origen.
- El README de la raíz explica: levantar todo, cargar OSM, crear el administrador
  (`create-admin`), cargar los datos de demostración y abrir el panel.
- Desarrollo del panel con `npm run dev` (Vite en su propio puerto, que también se añade a
  `CORS_ORIGINS` en desarrollo).

## 7. Datos de demostración

Las capturas necesitan un ranking y un mapa de calor con contenido. Se añade un comando
**`python -m app.cli seed-demo`** (y su opuesto **`seed-demo --remove`**) que:

- crea un ciudadano de demostración con correo de un dominio reservado (p. ej. `@demo.invalid`) y
  unos 25–40 reportes repartidos por vías reales de Pasto (distintas jerarquías, algunos cerca de
  servicios críticos, al menos uno sin vía para «Revisar vía»), con fotos genéricas incluidas en el
  repositorio y estados variados (con historial);
- **evalúa cada reporte con el motor real** (no inventa S, F, P ni U);
- cubre los **tipos** de caso de la tabla de la guía 8.3 (las tres severidades, las jerarquías primary/secondary/tertiary/residential, distancias ≤ 100 m, intermedias y ≥ 500 m, y un reporte sin vía). **Decisión del asistente:** no se buscan los valores exactos de U de esa tabla (exigiría colocar cada punto a distancias exactas de servicios reales y dependería de los datos de OSM); esos valores ya los verifican las pruebas unitarias del motor;
- vive fuera de las migraciones (guía 5) y se puede borrar entero.

En el panel, los reportes de demostración no se distinguen (son datos normales para el sistema); la
salvaguarda está en el documento: las capturas se presentan como **demostración de funcionamiento**,
no como resultados de campo. El registro en la bitácora lo deja escrito.

## 8. Qué queda al criterio de quien construye

- La disposición fina de cada pantalla, siguiendo el Figma (archivo
  `wjbs0QbgIJvRiduvFAimAI`, páginas del panel 1440×1000).
- El reparto en ramas (sugerido: backend de ranking/resumen/mapa; backend de detalle y estado;
  backend de pesos; base del panel con sesión; cada pantalla; datos de demostración; compose).
- El tamaño de página del ranking y los topes.
- Cómo se muestra el error 409 de pesos (sugerido: aviso con «Recargar la versión vigente»).

## 9. Decisiones tomadas en el diseño

- **Indicadores del encabezado** (decisión del responsable, 2026-11-08): Activos · Evaluados ·
  Priorizados · Reparados, en lugar de «prioridad alta» y «en intervención» del Figma, que no tienen
  definición en la tesis ni en la guía y exigirían una regla nueva. Se registra como propuesta
  aplicada en la bitácora y se ajusta el Figma.
- **Sesión del panel**: la de la decisión 42 (cookie `HttpOnly` para el refresco, CSRF, origen
  propio), ya aprobada.
- **Datos de demostración**: cubren los tipos de caso de la guía 8.3, no sus valores exactos
  (decisión del asistente).
- **Herramientas** de la sección 4: decisiones menores del asistente, por delegación del responsable.
