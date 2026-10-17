# Street Repo — Guía maestra de desarrollo

> Sistema Ciudadano de Reporte y Priorización de Daños en la Infraestructura Vial de Pasto, Nariño.
> Proyecto de grado · Ingeniería de Software · Universidad Cooperativa de Colombia, Campus Pasto.

Este archivo es la fuente de instrucciones para construir el software. Léelo completo antes de escribir código y vuelve a él cada vez que haya una duda de alcance, arquitectura o diseño.

> **Versionado de esta guía:** `AGENTS.md` es la **fuente canónica** y se versiona en git. `CLAUDE.md` es un archivo local, excluido de git, que solo contiene `@AGENTS.md` para que Claude Code lea este mismo contenido sin duplicarlo. **Edita siempre `AGENTS.md`** (también la bitácora de la sección 17) y confirma el cambio en una rama `docs/…` según la sección 8.4.

---

## 0. Cómo usar esta guía

### 0.1 Jerarquía de fuentes de verdad

Cuando dos fuentes se contradigan, manda la de mayor nivel:

1. **Documento de la tesis** (`CTG_07Septiembre_SantiagoArevalo_Ajustes_A1-A4.docx`): alcance, objetivos, historias de usuario, requisitos y reglas del modelo.
2. **Diagramas** (Lucid: ER y Clases): estructura de datos y de dominio.
3. **Diseño en Figma** (https://www.figma.com/design/wjbs0QbgIJvRiduvFAimAI): interfaz, flujos y tokens visuales.
4. **Esta guía**: stack, arquitectura y prácticas.

Si una fuente de menor nivel contradice a una de mayor nivel, **no decidas en silencio**: usa el protocolo de la sección 0.3.

### 0.2 Reglas de trabajo

- **No inventes requisitos.** Todo lo construido debe poder rastrearse a una historia de usuario, un requisito, una entidad del diagrama o una pantalla del diseño. Si no existe, pregunta.
- **Alcance de un avance de tesis.** Se construye un **MVP funcional**, no un producto comercial completo. Prefiere lo simple y correcto sobre lo sofisticado.
- **Los datos de ejemplo** del diseño (reportes, direcciones, puntajes) son solo ilustrativos. Úsalos como *fixtures* de prueba, nunca como datos reales.
- **El capítulo 4 de la tesis (resultados) está en pausa** hasta que exista el MVP. No generes resultados ni métricas inventadas.
- **Idioma:** interfaz y documentación en español; identificadores de código en inglés (ver sección 9.1).

### 0.3 Protocolo de mejoras y desviaciones (obligatorio)

Si detectas que algo del documento, los diagramas, el stack o el diseño **se puede mejorar** por buenas prácticas profesionales, estándares de la industria o aplicaciones análogas en cualquier ámbito (UX, seguridad, rendimiento, accesibilidad, arquitectura, datos, operación), **no lo apliques directamente**. En su lugar:

1. **Coméntalo** al responsable del proyecto antes de implementarlo.
2. Preséntalo con este formato breve:

```
Propuesta: <título corto>
Dónde: <documento / diagrama / diseño / stack / código>
Situación actual: <qué dice o hace hoy>
Mejora sugerida: <qué cambiarías>
Justificación: <práctica, estándar o caso análogo que la respalda>
Impacto: <alcance, esfuerzo, riesgo, efecto en la tesis>
Recomendación: aplicar / aplicar después del MVP / descartar
```

3. **Espera la decisión** y regístrala (sección 17, bitácora de decisiones).
4. Si la mejora cambia algo que la tesis ya afirma, indica qué sección del documento habría que ajustar.

Mientras no haya respuesta, implementa lo que dicen las fuentes y deja un `TODO(propuesta-N)` visible.

---

## 1. Contexto del producto

**Problema.** En Pasto los daños viales se reportan sin un criterio común de urgencia: los reportes se duplican, no se sabe cuáles atender primero y el ciudadano no ve qué pasó con el suyo.

**Solución.** Una app ciudadana (móvil) para reportar daños con foto y ubicación, y un panel administrativo (web) que **prioriza** los reportes con un modelo transparente y permite gestionar su estado.

**Actores.**
- **Ciudadano:** se registra, acepta la política de datos, reporta, confirma daños de otros, sigue sus reportes.
- **Administrador (Secretaría de Infraestructura):** ve el ranking y el mapa de calor, cambia estados, ajusta los pesos del modelo, carga datos OSM.

---

## 2. Modelo de dominio y reglas de negocio

### 2.1 Entidades (según diagramas ER y de Clases)

Consulta los diagramas para los atributos exactos. Entidades confirmadas en esta etapa:

- `usuario`
- `reporte`
- `confirmacion` (usuario ↔ reporte; **una por usuario y reporte**)
- `evaluacion` (resultado del cálculo de prioridad de un reporte)
- `servicio_critico` (escuelas, hospitales, etc., obtenidos de OSM)

Entidades y columnas añadidas por propuestas **aprobadas** (ya reflejadas en el ER de Lucid; ver bitácora, sección 17):
- `via.geom` y `via.highway_osm` (propuestas 6 y 7)
- `usuario.version_politica` (propuesta 8)
- `token_refresco` (propuesta 9)
- `solicitud_supresion` (propuesta 10)
- `reporte.clave_idempotencia` con restricción única (id_usuario, clave_idempotencia) (propuesta 11)

> Si necesitas una entidad o columna que no esté en los diagramas, aplica el protocolo 0.3.

### 2.2 Modelo de prioridad

```
U = 0,5·S + 0,3·F + 0,2·P        (escala 0–10)
```

Los pesos son **configurables** por el administrador y deben sumar exactamente 1,00 (validar en backend, no solo en la interfaz).

| Factor | Significado | Regla de normalización (0–10) |
|---|---|---|
| **S** | Severidad declarada por el ciudadano | baja = 3 · media = 6 · alta = 10 |
| **F** | Flujo vehicular aproximado por la jerarquía vial de OSM (`highway`) | primary = 10 · secondary = 7 · tertiary = 5 · residential / unclassified / service = 2 |
| **P** | Proximidad a servicios críticos | 10 si la distancia ≤ 100 m; decrece linealmente hasta 0 a 500 m |

**Casos especiales**
- **Sin vía asociada** (no hay vía OSM dentro de 30 m): `F = 2` y el reporte se marca **"Revisar vía"**.
- **Desempate del ranking:** mayor severidad → más confirmaciones → reporte más antiguo.
- Las **confirmaciones no modifican U**. Solo aportan al desempate y a la evidencia.

Fórmula de P (referencia):

```
d ≤ 100 m        → P = 10
100 m < d < 500  → P = 10 · (500 − d) / 400
d ≥ 500 m        → P = 0
```

**Precisión y redondeo (implementado en la fase 3, `priority/domain`):**
- Pesos con **dos decimales exactos** (`NUMERIC(3,2)`); se rechazan valores con más decimales, fuera de 0–1 o que no sumen 1,00.
- La distancia al servicio se redondea a **centímetros** y P se calcula **con esa distancia redondeada**, para que U se pueda reproducir con los valores guardados.
- P y U se redondean a **dos decimales, mitad hacia arriba** (`ROUND_HALF_UP`).
- Las reglas de S, F y P son funciones intercambiables (Strategy, `FactorRules`); el orden del ranking vive en `priority/domain/ranking.py` y la consulta SQL del ranking (fase 6) debe reproducirlo.

### 2.3 Parámetros geográficos

| Parámetro | Valor |
|---|---|
| Radio de deduplicación | 25 m |
| Radio de *map-matching* a la vía | 30 m |
| Radio de proximidad con P = 10 | 100 m |
| Radio máximo de proximidad (P) | 500 m |

Deben ser **constantes de configuración con nombre**, no números dentro de las consultas. Viven en `backend/app/shared/domain/geo_parameters.py`.

### 2.4 Estados del reporte

`Registrado → Evaluado → Priorizado → Reparado`

- Solo transiciones válidas, definidas en una única máquina de estados en el dominio.
- **Todo cambio de estado deja registro en el historial** (quién, cuándo, observación).
- Registrado → Evaluado ocurre por el cálculo automático del motor de priorización.

**Implementación actual (fase 3, `reports/domain/status_machine.py`):**
- Registrado → Evaluado **solo lo hace el sistema** (historial con `id_usuario` NULL); el resto de transiciones las hace una persona (el rol de administrador se verifica en la aplicación, fase 6).
- Un **recálculo** de prioridades no cambia el estado del reporte.
- La observación se recorta; una observación en blanco se guarda como NULL.
- **Avances con salto permitidos, retrocesos prohibidos** (decisión 12). Desde Evaluado se puede ir a Priorizado o directamente a Reparado (p. ej. una cuadrilla repara el daño antes de formalizar la prioridad); desde Priorizado, a Reparado. Reparado es final.
- Un reporte **Registrado** no puede saltar la evaluación: solo pasa a Evaluado, por el motor.
- Todo cambio, con o sin salto, queda en el historial.

### 2.5 Deduplicación

Al crear un reporte, buscar reportes activos dentro de 25 m (`ST_DWithin`). Si existen, mostrar la pantalla **Posible duplicado** y ofrecer **confirmar el existente** en lugar de crear uno nuevo. El ciudadano puede decidir crear uno nuevo de todos modos.

### 2.6 Historias de usuario (Pila del Producto de la tesis)

Úsalas para trazar cada commit y rama (`Refs: HU-xx`). Fuente: tabla de la Pila del Producto del documento; si la tesis cambia, esta tabla se actualiza.

| HU | Resumen | Prioridad | SP | Sprint |
|---|---|---|---|---|
| HU-01 | Documento de requisitos validado | Alta | 5 | 0 |
| HU-02 | Campos obligatorios del reporte (foto, GPS, severidad) | Alta | 3 | 0 |
| HU-03 | Modelo matemático ponderado de priorización | Alta | 8 | 1 |
| HU-04 | Arquitectura tecnológica del sistema | Alta | 5 | 1 |
| HU-05 | API para recibir reportes y calcular su puntaje de urgencia | Alta | 8 | 3 |
| HU-06 | Base de datos georreferenciada | Alta | 5 | 2 |
| HU-07 | Capturar foto y ubicación desde el celular y enviarlas | Alta | 8 | 5 |
| HU-08 | Mapa de calor y listado priorizado (panel) | Alta | 8 | 6 |
| HU-09 | Comparar el ranking con el panel de referencia | Media | 5 | 7 |
| HU-10 | Registro e inicio de sesión (JWT, roles) | Alta | 5 | 3 |
| HU-11 | Política de tratamiento de datos (Ley 1581) | Alta | 3 | 5 |
| HU-12 | Cambiar el estado del reporte con historial | Alta | 5 | 4 |
| HU-13 | Cargar desde OSM hospitales, escuelas y jerarquía vial | Alta | 8 | 2 |
| HU-14 | Configurar pesos w₁, w₂, w₃ (suma = 1) | Media | 3 | 5 |
| HU-15 | Aviso de reporte activo a menos de 25 m | Alta | 5 | 4 |
| HU-16 | Confirmar un reporte existente | Media | 3 | 4 |
| HU-17 | Backend y BD en Docker con HTTPS | Alta | 5 | 6 |
| HU-18 | Pruebas unitarias del motor e integración de la API | Media | 5 | 7 |

---

## 3. Stack tecnológico (fijo)

| Capa | Tecnología |
|---|---|
| App ciudadana | **Flutter** |
| Panel administrativo | **React + Leaflet** (el mapa de calor requiere un plugin) |
| API | **FastAPI** (Python) |
| Autenticación | **JWT** |
| Base de datos | **PostgreSQL + PostGIS** |
| Cartografía y datos viales | **OpenStreetMap**, **Nominatim**, **Overpass API** |
| Contenedores | **Docker** (+ Docker Compose para desarrollo) |

Cualquier herramienta adicional (ORM, gestor de estado, librería de pruebas, linter) es una **decisión menor que debes documentar**; cambiar una tecnología de esta tabla requiere el protocolo 0.3.

### 3.1 Uso responsable de servicios OSM

- **Nominatim** tiene política de uso público: máximo 1 solicitud por segundo, `User-Agent` identificable, sin uso masivo. Cachear resultados y no geocodificar en cada pulsación.
- **Overpass API** no debe consultarse en cada reporte. **Cargar los datos viales y de servicios críticos a PostGIS** (carga inicial/periódica, historia HU-13) y hacer el cálculo de F y P **localmente**. Así el sistema no depende de un servicio externo en tiempo de ejecución.
- Mostrar la **atribución obligatoria de OpenStreetMap** en todos los mapas.
- Los *tiles* públicos de OSM no son para tráfico alto: para el MVP basta, pero deja el proveedor de *tiles* configurable por variable de entorno.

---

## 4. Arquitectura

### 4.1 Principios

- **Monolito modular** para el backend: una sola aplicación desplegable, con módulos de dominio con límites claros. Es la opción adecuada para un MVP de tesis; evita la complejidad de microservicios.
- **Arquitectura por capas con inversión de dependencias** (estilo hexagonal / limpia): el dominio no depende de FastAPI, SQL ni librerías externas.
- **Separación de responsabilidades** y **alta cohesión, bajo acoplamiento**.
- **Explícito sobre implícito.** Sin magia: dependencias inyectadas, configuración centralizada.

### 4.2 Capas del backend

```
presentation/   → routers FastAPI, esquemas de entrada/salida (DTO), manejo de errores HTTP
application/    → casos de uso (CrearReporte, ConfirmarReporte, CambiarEstado, RecalcularPrioridades…)
domain/         → entidades, objetos de valor, reglas (modelo U, máquina de estados), interfaces de repositorio
infrastructure/ → repositorios SQL/PostGIS, cliente Nominatim, almacenamiento de fotos, seguridad, config
```

Regla de dependencia: `presentation → application → domain ← infrastructure`.

### 4.3 Estructura sugerida del repositorio

```
street-repo/
├─ docs/                      # tesis, diagramas exportados, ADRs, esta guía
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ core/                # config, seguridad, logging, errores
│  │  ├─ modules/
│  │  │  ├─ auth/ users/ reports/ confirmations/ priority/ roads/ critical_services/ admin/
│  │  │  │   └─ (cada uno con presentation/ application/ domain/ infrastructure/)
│  │  └─ shared/              # utilidades transversales mínimas
│  ├─ migrations/             # Alembic
│  ├─ tests/ (unit/ integration/ e2e/)
│  └─ pyproject.toml
├─ admin-web/                 # React + Leaflet
├─ mobile/                    # Flutter
├─ infra/                     # docker-compose, Dockerfiles, scripts de carga OSM
└─ .github/workflows/         # CI
```

### 4.4 Patrones de diseño recomendados

Úsalos **cuando resuelvan un problema real**, no por decoración.

| Patrón | Dónde aplicarlo |
|---|---|
| **Repository** | Acceso a datos detrás de interfaces del dominio; permite probar sin base de datos |
| **Service / Use case** | Un caso de uso por operación de negocio, con una sola responsabilidad |
| **Strategy** | Cálculo de cada factor (S, F, P) y normalización; facilita ajustar reglas tras el panel de expertos |
| **State** (o tabla de transiciones) | Máquina de estados del reporte |
| **Factory** | Construcción de entidades válidas desde datos externos |
| **Adapter / Gateway** | Nominatim, Overpass, almacenamiento de archivos: el dominio ve una interfaz propia |
| **Dependency Injection** | `Depends` de FastAPI; en Flutter y React, inyección por contexto/proveedores |
| **Unit of Work** | Transacciones que abarcan varios repositorios (crear reporte + evaluación + historial) |
| **Observer / eventos de dominio** | Reaccionar a "reporte creado/confirmado/estado cambiado" (recalcular, registrar historial) sin acoplar módulos |
| **DTO / Mapper** | Separar los esquemas de la API de las entidades del dominio |

Evita: lógica de negocio en routers o en widgets, *god classes*, consultas SQL dispersas, singletons globales con estado.

### 4.5 Recalculado de prioridades

- Cuando el administrador guarda nuevos pesos, **recalcular las evaluaciones de los reportes activos** en una transacción y registrar la versión de configuración usada.
- Mantener **versionado de configuración de pesos** (la pantalla "Versiones de configuración" lo muestra).
- El cálculo debe ser **determinista y reproducible**: guardar en `evaluacion` los valores S, F, P, los pesos y U, y la fecha del cálculo.

**Implementación actual (fase 3):**
- Cada cálculo es una **fila nueva** de `evaluacion_prioridad` que referencia la versión de pesos (`id_config`), el servicio crítico y su distancia. El reporte guarda una copia de la U vigente (`puntaje_prioridad`) y la vía asociada (`id_via`; NULL = "Revisar vía").
- Guardar pesos crea una **versión nueva vigente**; las anteriores se conservan y no se editan (índice único parcial: una sola vigente).
- Se recalculan los **reportes activos** (todo estado salvo Reparado; decisión 13) en **una sola transacción**: si un recálculo falla, se revierte todo y sigue vigente la versión anterior.
- `ReportEvaluator` no confirma la transacción; la controla el caso de uso que lo llama (`UpdateWeights` y, en la fase 5, la creación del reporte).

---

## 5. Base de datos y datos geográficos

- **SRID 4326** (WGS 84) para almacenar; usar el tipo `geography` o transformar a un sistema métrico para medir distancias de forma correcta. Elegir una opción y documentarla.
- **Índices GiST** sobre toda columna geométrica usada en `ST_DWithin` / `ST_Distance`.
- Usar `ST_DWithin` para filtrar (aprovecha índice) y `ST_Distance` solo para el valor exacto.
- **Migraciones versionadas con Alembic**; nunca modificar el esquema a mano.
- **Integridad:** claves foráneas, `NOT NULL`, `CHECK` (p. ej. pesos entre 0 y 1, severidad válida), restricción **única (usuario, reporte)** en `confirmacion`.
- **Consultas parametrizadas siempre.** Prohibido concatenar texto en SQL.
- Paginación en todos los listados; sin `SELECT *` en consultas de producción.
- **Datos de prueba** en *seeds*/fixtures separados de las migraciones.
- Tarea de **carga de datos OSM** (vías con `highway`, servicios críticos) como script idempotente y repetible.

---

## 6. API (FastAPI)

### 6.1 Diseño

- REST, recursos en plural, JSON, versionada: `/api/v1/...`.
- Esquemas **Pydantic** estrictos para entrada y salida; nunca devolver entidades de base de datos directamente.
- Códigos HTTP correctos (201 creación, 204 sin contenido, 400/422 validación, 401/403 acceso, 404, 409 conflicto, 429 límite).
- **Formato de error uniforme** (código estable, mensaje en español, detalle de campo cuando aplique), por ejemplo `{ "code": "REPORT_DUPLICATE_NEARBY", "message": "...", "details": {...} }`.
- Documentación **OpenAPI** generada y revisada; es el contrato con Flutter y React.
- Idempotencia donde aplique (envío de reporte con una clave de idempotencia para evitar duplicados por reintentos de red móvil).
- Paginación por cursor o `limit/offset` con tope máximo.

### 6.2 Endpoints orientativos (a validar contra historias de usuario)

```
POST   /api/v1/auth/register            POST /api/v1/auth/login        POST /api/v1/auth/refresh
GET    /api/v1/reports                  (mapa, filtros, paginación)
POST   /api/v1/reports                  (foto, ubicación, severidad, descripción)
GET    /api/v1/reports/{id}
GET    /api/v1/reports/nearby           (deduplicación)
POST   /api/v1/reports/{id}/confirmations
GET    /api/v1/me/reports
POST   /api/v1/me/data-deletion-requests   (supresión, Ley 1581)
GET    /api/v1/admin/ranking            GET /api/v1/admin/heatmap
PATCH  /api/v1/admin/reports/{id}/status
GET/PUT /api/v1/admin/weights           GET /api/v1/admin/weights/versions
POST   /api/v1/admin/osm/import
```

---

## 7. Seguridad

La seguridad no es una fase final; se aplica desde el primer commit. Referencia: **OWASP ASVS**, **OWASP Top 10** y **OWASP Mobile Top 10**.

### 7.1 Autenticación y autorización

- Contraseñas con **Argon2id** (o bcrypt con coste adecuado). Nunca en texto plano ni con hash rápido.
- **JWT** de acceso con vida corta (p. ej. 15 min) + **token de refresco** rotatorio con vida más larga y revocable. Firmar con secreto fuerte desde variables de entorno; fijar el algoritmo explícitamente en la verificación; validar `exp`, `iat`, `sub`.
- **Control de acceso por rol (RBAC)** en el backend: ciudadano vs. administrador. **Toda ruta administrativa verifica el rol en el servidor**, aunque la interfaz oculte los botones.
- **Autorización por objeto:** un ciudadano solo ve y modifica lo suyo (evitar IDOR). Un usuario solo confirma un reporte una vez.
- Limitar intentos de inicio de sesión (**rate limiting** + bloqueo progresivo).

### 7.2 Datos personales (Ley 1581 de 2012, Colombia)

- **Consentimiento informado y registrado** (fecha y versión de la política) antes de tratar datos personales; la pantalla "Política de datos" es obligatoria en el flujo de registro.
- Derechos del titular: **conocer, actualizar y solicitar supresión** de sus datos (pantalla Perfil). Implementar el flujo, no solo el botón.
- **Minimización:** recoger solo lo necesario; no exponer correo, nombre ni coordenadas exactas de otros usuarios en vistas públicas.
- **Fotos:** eliminar metadatos EXIF (puede contener ubicación y dispositivo) y reescalar en el servidor. Validar tipo real (no solo extensión), tamaño máximo y recodificar la imagen.
- No registrar datos personales en logs.

### 7.3 Protección de la aplicación

- **Validación de entrada en el servidor** siempre (la validación del cliente es solo UX). Listas permitidas sobre listas bloqueadas.
- **Consultas parametrizadas / ORM** (anti inyección SQL). Escapado de salida y sin `dangerouslySetInnerHTML` en React.
- **CORS** restrictivo (solo el origen del panel). **Cabeceras de seguridad** (HSTS, `X-Content-Type-Options`, CSP, `Referrer-Policy`).
- **HTTPS obligatorio** fuera de desarrollo.
- **Secretos** solo por variables de entorno/gestor de secretos; **jamás en el repositorio**. Incluir `.env.example` sin valores reales y `.gitignore` adecuado.
- **Rate limiting** global y más estricto en login, registro y creación de reportes (anti abuso/spam).
- **Dependencias:** fijar versiones, auditar (`pip-audit`, `npm audit`, `flutter pub outdated`) y activar Dependabot o equivalente.
- Contenedores: imagen base mínima, usuario no root, sin secretos en capas, `healthcheck`.
- Manejo de errores sin filtrar trazas ni detalles internos al cliente.
- **Flutter:** guardar tokens en almacenamiento seguro (Keychain/Keystore, `flutter_secure_storage`), no en preferencias planas; permisos de cámara y ubicación solicitados en contexto y con explicación.
- **React:** el token del panel no debe quedar en `localStorage` si se puede evitar (preferir cookie `HttpOnly` + `SameSite` o memoria con refresco); protección CSRF si se usan cookies.

### 7.4 Anti-abuso del dominio

- Evitar manipulación del ranking: la severidad la declara el ciudadano, pero **la confirmación no altera U** (decisión de diseño que se mantiene). Detectar ráfagas de reportes del mismo usuario/zona.
- Ubicaciones fuera del área de Pasto: validar contra un límite geográfico configurable.

---

## 8. Buenas prácticas de código (aplican a los tres proyectos)

### 8.1 Principios

- **SOLID**, **DRY** sin abstracciones prematuras, **KISS**, **YAGNI**.
- Funciones pequeñas con un único propósito; nombres que revelan intención; sin números ni cadenas "mágicas" (constantes con nombre; ver 2.3).
- **Tipado estático**: type hints completos en Python (verificados con `mypy`), Dart con *null safety*, TypeScript en modo `strict` para el panel.
- Inmutabilidad por defecto en objetos de valor y DTO.
- Manejo de errores explícito: excepciones de dominio propias, sin `except:` desnudo ni errores silenciados.
- Comentarios para el **porqué**, no para el qué; docstrings en la API pública del dominio.
- Sin código muerto ni `TODO` sin dueño ni propuesta asociada.

### 8.2 Herramientas por proyecto

| Proyecto | Formato / lint | Tipos | Pruebas |
|---|---|---|---|
| Backend | `ruff` (+ `ruff format`) | `mypy --strict` en dominio y aplicación | `pytest`, `pytest-cov`, `httpx` |
| Panel web | `eslint` + `prettier` | `tsc --noEmit` (`strict`) | `vitest` + Testing Library, `Playwright` para E2E |
| App móvil | `flutter analyze` + `dart format` | null safety | `flutter test`, pruebas de widgets, `integration_test` |

Configurar **pre-commit** para ejecutar formato y lint antes de cada commit.

### 8.3 Pruebas

- **Regla por fase:** en **cada fase del plan (sección 13) se escriben y ejecutan pruebas unitarias** para todo servicio, caso de uso, regla de dominio y componente nuevo. Las pruebas se escriben **junto con el código** (idealmente antes o a la par), no al final. Una fase **no se da por cerrada** si sus pruebas no existen o no pasan; al cerrarla se informa cuántas pruebas se ejecutaron y su resultado.
- **Las pruebas son la forma de saber si los servicios funcionan.** Cada servicio (autenticación, reportes, deduplicación, confirmaciones, priorización, cambio de estado, pesos, carga OSM) debe tener pruebas unitarias de su lógica y, cuando toque base de datos o PostGIS, pruebas de integración. Si algo falla o se modifica, se vuelven a ejecutar todas las pruebas afectadas (regresión).
- **Pirámide de pruebas:** muchas unitarias (dominio puro: modelo U, normalizaciones, máquina de estados), algunas de integración (repositorios contra PostGIS real en Docker), pocas E2E (flujos críticos).
- **El modelo de priorización debe tener pruebas exhaustivas** con casos de borde: d = 100 m, d = 500 m, sin vía asociada, pesos que no suman 1, empates.
- Usar como casos de prueba los **datos de ejemplo del diseño** (valores esperados verificables):

| Reporte | S | F | P | U esperada |
|---|---|---|---|---|
| Av. Los Estudiantes | 10 | 7 | 8,0 | **8,70** |
| Calle 16 con Panamericana | 6 | 10 | 10,0 | **8,00** |
| Carrera 27 | 10 | 5 | 3,75 (d = 350 m) | **7,25** |
| Calle 18 con Carrera 27 | 6 | 5 | 10,0 | **6,50** |
| Carrera 22 | 6 | 7 | 5,0 | **6,10** |
| Sector Obonuco (sin vía) | 6 | 2 | 0,0 | **3,60** · marcado "Revisar vía" |

- Cobertura mínima objetivo: **≥ 80 %** en dominio y aplicación del backend.
- Las pruebas deben ser deterministas, independientes entre sí y rápidas.

### 8.4 Control de versiones y CI/CD

#### Reglas de publicación en GitHub (obligatorias)

- **Cada mejora o implementación se desarrolla en su propia rama nueva** creada desde `main` actualizada. **Nunca se abre un Pull Request**: la integración a `main` se hace directamente (ver "Flujo de ramas" más abajo).
- **Se suben siempre los cambios de importancia media o alta**: una funcionalidad completa o un avance verificable, una corrección de errores, cambios de esquema o migraciones, reglas de negocio, seguridad, configuración de infraestructura/CI y documentación relevante. Los cambios triviales (un typo, un ajuste de formato aislado) se agrupan con el siguiente cambio relevante.
- **Antes de subir:** ejecutar lint, verificación de tipos y **todas las pruebas unitarias del código tocado**. No se sube con pruebas fallando.
- **Commits detallados**, con **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`):
  - Una línea de resumen en imperativo, de máximo ~72 caracteres, con alcance cuando aplique (`feat(priority): calcular proximidad P con ST_DWithin`).
  - Un cuerpo que explique **qué cambió, por qué y cómo se verificó** (pruebas ejecutadas y resultado), más cualquier decisión, limitación o `TODO` asociado.
  - Referencia a la historia de usuario o al número de propuesta de la bitácora cuando exista (`Refs: HU-05`, `Refs: propuesta-3`).
  - **Un commit por cambio lógico**; no mezclar funcionalidades, correcciones y refactors en un mismo commit.
- **Nunca** subir secretos, archivos `.env`, datos personales ni artefactos de compilación (revisar `git status` y `git diff --staged` antes de cada commit).
- No reescribir la historia de `main` (`push --force` prohibido).

#### Flujo de ramas (una rama por mejora o implementación)

**Recomendación del asistente para este proyecto:** flujo *trunk-based* ligero, con ramas cortas y de un solo propósito, integradas por *merge* local sin PR. Es el equilibrio adecuado para un MVP de tesis con un solo desarrollador: conserva el historial ordenado por funcionalidad, permite descartar un experimento sin ensuciar `main` y no añade el ritual de revisión de un equipo.

1. **Crear la rama** desde `main` actualizada (`git switch main && git pull && git switch -c <tipo>/<alcance>-<descripcion>`).
2. **Nombres:** `<tipo>/<alcance>-<descripcion-corta>` en minúsculas y con guiones, con los mismos tipos de Conventional Commits:
   - `feat/` funcionalidad nueva · `fix/` corrección · `refactor/` · `test/` · `docs/` · `chore/` (infraestructura, CI, dependencias)
   - `improve/` **mejora aprobada** de la bitácora (sección 17), con el número de propuesta
   - Ejemplos: `feat/priority-modelo-urgencia`, `feat/reports-deduplicacion-25m`, `fix/auth-expiracion-refresh`, `improve/propuesta-04-estados-vacios`
3. **Una rama = un objetivo.** Si surge algo ajeno, se abre otra rama. Una mejora y una implementación nunca comparten rama.
4. **Subir la rama** al remoto con frecuencia (`git push -u origin <rama>`) para respaldar el trabajo; los commits siguen las reglas de arriba.
5. **Antes de integrar:** la rama debe estar al día con `main` (`git rebase main` o `git merge main` en la rama), con lint, tipos y pruebas unitarias pasando.
6. **Integrar sin PR:** desde `main`, `git merge --no-ff <rama>` (deja un commit de fusión que agrupa la funcionalidad y facilita revertirla), luego `git push origin main`. Si la rama tiene un solo commit limpio, vale `--ff-only`.
7. **Verificar la CI en `main`** tras la integración. Si falla, corregir de inmediato.
8. **Eliminar la rama** local y remota una vez integrada (`git branch -d <rama>` y `git push origin --delete <rama>`).
9. **Las mejoras propuestas con el protocolo 0.3** solo se implementan, en su rama `improve/…`, **después de que el responsable las apruebe**. La rama debe incluir en la descripción del último commit el resumen de la propuesta y su recomendación (aplicar / aplicar después del MVP / descartar).
10. **Recomendación explícita en cada rama:** al abrir o cerrar una rama, el asistente informa al responsable en una línea: qué contiene, su evaluación (riesgo, pruebas, impacto en la tesis) y su recomendación de integrarla, posponerla o descartarla. Si la recomendación es descartar, la rama no se integra y se elimina tras avisar.

Ejemplo de commit:

```
feat(priority): calcular urgencia U con pesos configurables

Implementa el modelo U = w1·S + w2·F + w3·P con normalizaciones de
severidad, jerarquía vial OSM y proximidad (100 m → 10, 500 m → 0).
Marca "Revisar vía" y asigna F = 2 cuando no hay vía a 30 m.

Verificación: pytest tests/unit/priority → 24 pruebas OK
(casos de borde d = 100 m, d = 500 m, sin vía, empates).
Refs: HU-03
```

> Los números de historia de usuario salen de la tabla de la sección 2.6 (tomada de la Pila del Producto de la tesis). No inventes ni copies números de ejemplos: verifícalos en esa tabla.

#### Integración continua

- **CI** (GitHub Actions u otro) en cada *push* a `main`: lint, tipos, pruebas, auditoría de dependencias y construcción de imágenes Docker. Si la CI falla, **corregir de inmediato con un commit nuevo** antes de seguir con otra funcionalidad.
- **Versionado semántico** y `CHANGELOG`.
- Despliegue reproducible con Docker Compose; variables por entorno (`dev`, `test`, `prod`).

### 8.5 Observabilidad

- **Logs estructurados (JSON)** con identificador de correlación por petición; niveles correctos; sin datos personales.
- Endpoint `/health` (vivo) y `/ready` (base de datos disponible).
- Métricas básicas (latencia, errores, tiempo de cálculo de prioridad) si el tiempo lo permite.

---

## 9. Convenciones

### 9.1 Nombres

- **Código** en inglés (`Report`, `CriticalService`, `priority_score`); **textos de interfaz y mensajes** en español.
- Python: `snake_case` / `PascalCase` para clases. Dart: `lowerCamelCase` / `UpperCamelCase`, archivos `snake_case`. TypeScript: `camelCase` / `PascalCase`.
- Tablas y columnas de base de datos: seguir los nombres de los diagramas ER (`snake_case`); si difieren de los nombres del código, documentar el mapeo.
- Un término de dominio, un nombre: mantener un glosario (reporte, confirmación, evaluación, severidad, flujo, proximidad, urgencia).

### 9.2 Textos y formato

- Interfaz en **español de Colombia**. Decimales con **coma** en la interfaz (`8,70`); con **punto** en la API y la base de datos.
- Fechas ISO 8601 en la API (UTC); mostrar en hora de Bogotá (UTC−5) en la interfaz, con formato corto ("13 oct").
- Mensajes de error claros, accionables y sin culpar al usuario.

---

## 10. Diseño de interfaz (basado en Figma)

Fuente: https://www.figma.com/design/wjbs0QbgIJvRiduvFAimAI (14 pantallas). Mantén **fidelidad** al diseño; las mejoras se proponen con el protocolo 0.3.

### 10.1 Tokens

| Token | Valor |
|---|---|
| Tinta (texto/oscuro) | `#1B2430` |
| Papel (fondo) | `#F5F3EE` |
| Ámbar (acción/acento) | `#F5B800` |
| Línea (bordes) | `#E2DED5` |
| Texto secundario | `#5B6573` |
| Estado **Registrado** | gris `#5B6573` (chip `#E8EAEE` / `#3D4756`) |
| Estado **Evaluado** | azul `#2B6CB0` (chip `#D9E8F7` / `#1C4E80`) |
| Estado **Priorizado** | ámbar `#B7791F` (chip `#FDF0C4` / `#7A4E00`) |
| Estado **Reparado** | verde `#1F7A5C` (chip `#DDF1E8` / `#14573F`) |
| Severidad baja / media / alta | `#2B6CB0` / `#B45F06` / `#B42318` |
| Tipografía títulos | **Archivo** 700/800 |
| Tipografía cuerpo | **Manrope** 400–700 |

Implementarlos como **tokens centralizados** (tema de Flutter, variables CSS / objeto de tema en React), nunca como colores sueltos en los componentes.

### 10.2 Pantallas y mapa de funcionalidad

**App ciudadana (390×844)**

| Pantalla | Propósito |
|---|---|
| Bienvenida | Presentación y entrada |
| Iniciar sesión / Registro | Acceso |
| Política de datos (Ley 1581) | Consentimiento informado |
| Mapa de reportes | Ver reportes cercanos, filtrar |
| Nuevo reporte · Foto y ubicación | Captura de evidencia |
| Nuevo reporte · Severidad | Severidad y descripción |
| Posible duplicado | Confirmar el reporte existente (≤ 25 m) |
| Reporte enviado | Confirmación y estado inicial |
| Detalle del reporte | Estado, historial, confirmar |
| Mis reportes | Seguimiento |
| Perfil y privacidad | Datos, política, supresión, cerrar sesión |

**Panel administrativo (1440×1000)**

| Pantalla | Propósito |
|---|---|
| Priorización | Mapa de calor + ranking con S/F/P/U y chip "Revisar vía" |
| Detalle y estado | Evidencia, vía OSM, desglose del cálculo, cambio de estado con observación, historial |
| Pesos del modelo | Sliders w₁/w₂/w₃, validación Σ = 1,00, reglas (solo lectura), versiones |

> Hay historias de usuario (carga de datos OSM, HU-13; comparación con panel de expertos, HU-09) que **no tienen pantalla diseñada todavía**. El ítem "Datos OSM" del menú del panel existe sin pantalla. Antes de construirlas, propón su diseño con el protocolo 0.3.

### 10.3 Buenas prácticas de interfaz

- **Accesibilidad (WCAG 2.2 AA):** contraste mínimo 4,5:1 en texto; **áreas táctiles ≥ 44 px** (el diseño ya las usa); no comunicar estado solo por color (los chips llevan texto); etiquetas asociadas a cada campo; foco visible; soporte de lector de pantalla (`Semantics` en Flutter, ARIA correcta en React); respetar tamaño de texto del sistema.
- **Estados completos en cada pantalla:** cargando (esqueletos), vacío, error con reintento, sin conexión y éxito. El diseño muestra el caso feliz; **diseña e implementa también los demás** y propónlos como mejora si hace falta.
- **Formularios:** validación en línea clara, conservar lo escrito ante un error, deshabilitar el envío doble, indicar progreso (pasos 1 de 2).
- **Móvil con red inestable:** cola de envío con reintento, compresión de fotos antes de subir, tolerancia a pérdida de conexión durante el reporte.
- **Feedback inmediato** a toda acción (confirmación visual, mensajes breves).
- **Consistencia:** un único conjunto de componentes reutilizables (botón, chip de estado, tarjeta, campo, barra de navegación). Chips de estado y severidad centralizados.
- **Mapa:** mostrar atribución de OSM; agrupar marcadores (*clustering*) con muchos puntos; no depender solo del color en el mapa de calor (incluir leyenda y números).
- **Privacidad en la interfaz:** coordenadas aproximadas para terceros; el nombre del reportante solo en el panel administrativo.
- **Panel web responsivo** desde ~1024 px y navegable por teclado.

### 10.4 Arquitectura del cliente

- **Flutter:** capas `presentation / application / domain / data` por funcionalidad (*feature-first*), gestor de estado unidireccional (Riverpod o Bloc: **elegir uno y registrar la decisión**), repositorios con interfaces, `go_router` para navegación, modelos inmutables.
- **React:** componentes pequeños y tipados, *hooks* para lógica, capa de acceso a API aislada (cliente generado a partir de OpenAPI cuando sea posible), **TanStack Query** o equivalente para caché de servidor, rutas protegidas por rol.
- Ninguna regla de negocio (cálculo de U, transiciones) vive en el cliente: el cliente **muestra** lo que calcula el servidor.

---

## 11. Rendimiento

- Índices espaciales y de ordenamiento (U, estado, fecha) para el ranking.
- Paginar y limitar el mapa por área visible (*bounding box*).
- Precalcular y guardar U en `evaluacion`; recalcular solo ante cambio de pesos o de datos del reporte.
- Compresión y miniaturas de fotos; almacenamiento fuera de la base de datos (disco/objeto) con referencia en la tabla.
- Metas orientativas para el MVP: listados < 500 ms, envío de reporte < 3 s con red 4G.

---

## 12. Despliegue y operación

- `docker compose up` debe levantar **API + PostgreSQL/PostGIS + panel** con datos de ejemplo.
- Variables de entorno documentadas en `.env.example`.
- Migraciones automáticas controladas en el arranque (o paso explícito documentado).
- Respaldos de base de datos documentados (aunque sea manual en el MVP).
- `README` con: requisitos, arranque en 5 comandos, estructura, cómo correr pruebas y cómo cargar datos OSM.

---

## 13. Plan de construcción del MVP (propuesto)

Cada fase termina con algo **ejecutable y probado**. Ajusta el orden con el responsable si cambia el alcance.

**Cierre obligatorio de cada fase:**
1. Escribir y ejecutar las **pruebas unitarias** de lo construido (sección 8.3) y las de integración que apliquen.
2. Confirmar que **todo el conjunto de pruebas existente sigue pasando** (sin regresiones), con lint y tipos limpios.
3. **Integrar la rama de la fase a `main`** mediante *merge* directo y subirla, con commits detallados (sección 8.4), sin abrir PR. Cada funcionalidad o mejora dentro de la fase tiene su propia rama.
4. **Etiquetar la versión** de cierre con una etiqueta anotada SemVer (`v0.<n>.0` al cerrar la fase *n*), mover lo de «Sin publicar» del `CHANGELOG.md` a esa versión y subir la etiqueta (`git push origin <etiqueta>`).
5. Reportar al responsable: qué se construyó, cuántas pruebas pasaron, qué quedó pendiente y las propuestas de mejora (0.3).

1. **Cimientos:** repositorio, Docker Compose, PostgreSQL + PostGIS, FastAPI con `/health`, CI, linters, estructura de carpetas, migraciones base según el diagrama ER.
2. **Datos geográficos:** script de carga OSM (vías con `highway`, servicios críticos) a PostGIS; consultas de *map-matching* y proximidad con pruebas.
3. **Dominio y priorización:** modelo U, normalizaciones, máquina de estados, pesos versionados; pruebas con la tabla de la sección 8.3.
4. **Autenticación y usuarios:** registro con consentimiento, login, JWT + refresco, RBAC.
5. **Reportes:** crear (foto + ubicación + severidad), deduplicación a 25 m, confirmaciones, "mis reportes".
6. **Panel administrativo:** ranking, mapa de calor, detalle y cambio de estado con historial, pesos del modelo con recálculo.
7. **App Flutter:** flujos de la sección 10.2 con los tokens de la 10.1.
8. **Endurecimiento:** revisión de seguridad (7), accesibilidad (10.3), estados vacíos/error, rendimiento (11), documentación.

Al cerrar cada fase: actualizar el `README`, la bitácora (sección 17) y, si algo se desvió del documento, avisar para ajustar la tesis.

**Estado (2026-10-16):** fases 1, 2 y 3 cerradas e integradas en `main` (etiquetas `v0.1.0`, `v0.2.0` y `v0.3.0`), con la CI en verde (252 pruebas, cobertura del backend 99 %). Pendientes de la fase 3 que se completan después: rutas HTTP de pesos y versiones (`GET/PUT /admin/weights`) y el error 409 si dos administradores guardan pesos a la vez (fase 6); lanzar la evaluación al crear un reporte (fase 5).

**Avance de la fase 4 (2026-10-16, para retomar en la próxima sesión):**
- Hecho e integrado en `main` (CI en verde, 361 pruebas, cobertura 98 %):
  - Migración 0006 (`usuario.version_politica`, `token_refresco`, `solicitud_supresion`), commit `32f853c`.
  - Autenticación (commit `76e27f2`): registro con consentimiento, login Argon2id, JWT de acceso de 15 min, refresco rotatorio con detección de reutilización, logout, `GET /api/v1/me`, RBAC (`require_admin`) y `python -m app.cli create-admin`. Decisiones en `docs/adr/0004-autenticacion.md`.
- Pendiente, en este orden y cada uno en su rama:
  1. ~~`chore/sonarcloud`: aplicar la propuesta 22~~ (hecho).
  2. ~~`feat/auth-limite-intentos`~~ (hecho, decisión 25): bloqueo progresivo por correo y límite por IP en login y registro, en memoria del proceso; el límite de reportes llega en la fase 5.
  3. `feat/users-derechos-titular`: `PATCH /api/v1/me` (actualizar) y `POST /api/v1/me/data-deletion-requests` con supresión **inmediata** por anonimización (decisión 23).
  4. Cierre de la fase 4: README, CHANGELOG, etiqueta `v0.4.0` y versión del backend.

---

## 14. Definición de terminado (DoD)

Una funcionalidad está **terminada** solo si:

- [ ] Cumple la historia de usuario y los criterios de aceptación del documento.
- [ ] Respeta diagramas, diseño y las reglas de la sección 2.
- [ ] Tiene **pruebas unitarias** (y de integración si aplica) que pasan en local y en CI.
- [ ] Se desarrolló en su propia rama, se integró a `main` por *merge* directo con commits detallados, sin PR, y la rama se eliminó.
- [ ] Pasa lint, formato y verificación de tipos sin advertencias nuevas.
- [ ] Valida entradas en el servidor y aplica control de acceso por rol/objeto.
- [ ] Contempla estados de carga, vacío y error en la interfaz.
- [ ] No expone secretos ni datos personales en logs, errores ni repositorio.
- [ ] La API está documentada (OpenAPI) y el `README`/docs actualizados.
- [ ] Las desviaciones y mejoras propuestas quedaron registradas (sección 17).

---

## 15. Lista de verificación de seguridad (pre-entrega)

- [ ] Contraseñas con Argon2id/bcrypt; sin secretos en el repositorio.
- [ ] JWT de vida corta, refresco rotatorio y verificación estricta del algoritmo.
- [ ] RBAC en servidor en todas las rutas `/admin`; sin IDOR.
- [ ] Consultas 100 % parametrizadas.
- [ ] CORS restringido, cabeceras de seguridad, HTTPS.
- [ ] Rate limiting en login, registro y reportes.
- [ ] Fotos: validación real de tipo, límite de tamaño, EXIF eliminado.
- [ ] Consentimiento Ley 1581 registrado; flujos de consulta, actualización y supresión operativos.
- [ ] Auditoría de dependencias sin vulnerabilidades altas/críticas.
- [ ] Contenedores sin root; logs sin datos personales.
- [ ] Almacenamiento seguro de tokens en móvil y panel.

---

## 16. Qué NO hacer

- No cambiar el stack, el modelo U ni los parámetros (25 m, 30 m, 100/500 m) sin aprobación.
- No inventar entidades, endpoints, pantallas ni datos reales.
- No dejar lógica de negocio en routers, widgets o componentes.
- No hacer commits con secretos, datos personales o archivos de `.env`.
- **No abrir Pull Requests.** Tampoco desarrollar en `main` ni mezclar varias mejoras o implementaciones en una misma rama: cada una va en su rama y se integra por *merge* directo.
- No subir cambios sin pruebas unitarias ejecutadas, ni dar una fase por terminada con pruebas fallando.
- No hacer commits vagos ("update", "fix", "cambios"): cada commit explica qué, por qué y cómo se verificó.
- No llamar a Nominatim/Overpass en cada solicitud del usuario.
- No presentar los datos de ejemplo como resultados de la tesis.
- No escribir el capítulo 4 ni métricas de validación antes de tener el MVP.

---

## 17. Bitácora de decisiones y propuestas

Mantén esta tabla actualizada (o un directorio `docs/adr/` con un archivo por decisión).

| # | Fecha | Tipo | Descripción | Estado |
|---|---|---|---|---|
| 1 | — | Decisión menor | Gestor de estado en Flutter (Riverpod / Bloc) | Pendiente |
| 2 | 2026-10-15 | Decisión menor | Herramientas del backend: SQLAlchemy 2 + GeoAlchemy2 + psycopg 3, uv, Python 3.13 (`docs/adr/0002-herramientas-backend.md`) | Aceptada |
| 3 | — | Propuesta | Diseñar pantallas faltantes: carga de datos OSM (HU-13) y comparación con expertos (HU-09) | Pendiente |
| 4 | — | Propuesta | Diseñar estados vacío, carga, error y sin conexión de cada pantalla | Pendiente |
| 5 | — | Propuesta | Documentar en la tesis los límites de uso de Nominatim, Overpass y *tiles* de OSM | Pendiente |
| 6 | 2026-10-15 | Propuesta (ER) | Geometría de la vía: `via.geom GEOMETRY(LineString, 4326)` con índice GiST; distancias en metros (`geography` o transformación a sistema métrico, documentar la elección) | **Aplicada** (2026-10-15) · migración 0003 · se eligió `geography` (decisión 17) · ER actualizado |
| 7 | 2026-10-15 | Propuesta (ER / tesis) | Correspondencia `highway` → `jerarquia_vial`: `trunk`, `primary` y sus `_link` → primaria; `secondary` → secundaria; `tertiary` → terciaria; `residential`, `unclassified`, `service`, `living_street` → residencial; el resto no se carga. Se añade `via.highway_osm VARCHAR(30)` con la etiqueta original para auditoría. Verificar con datos de Pasto si la Panamericana es `trunk` | **Aplicada** (2026-10-15) · `roads/domain/classification.py`, migración 0004 · confirmado: 19 de 61 tramos de la Panamericana son `trunk`/`trunk_link` · ER actualizado · pendiente explicitar la regla en la sección del factor F de la tesis |
| 8 | 2026-10-15 | Propuesta (ER) | `usuario.version_politica VARCHAR(20)`: versión de la política de datos aceptada (Ley 1581) | **Aprobada** · aplicar en la fase 4 · ER actualizado |
| 9 | 2026-10-15 | Propuesta (ER) | Tabla `token_refresco` (id, id_usuario, hash del token, emitido, expira, revocado, reemplazado_por): refresco rotatorio y revocable. Guardar solo el hash; si se reutiliza un token ya usado, revocar toda la cadena de la sesión | **Aprobada** · aplicar en la fase 4 · ER actualizado |
| 10 | 2026-10-15 | Propuesta (ER / tesis) | Supresión por anonimización: borrar nombre, correo y hash, desactivar la cuenta y conservar los reportes. Incluir en la anonimización el texto libre de la descripción y las fotos con rostros o placas. Tabla `solicitud_supresion` (id, id_usuario, estado, fecha_solicitud, fecha_atencion) para dejar constancia del trámite. Validar el criterio con la asesoría de la universidad | **Aprobada** · aplicar en la fase 4 · ER actualizado · pendiente describir el tratamiento en la tesis |
| 11 | 2026-10-15 | Propuesta (ER) | Idempotencia en la creación de reportes: `reporte.clave_idempotencia UUID` (opcional), cabecera `Idempotency-Key`; **única por par (usuario, clave)** y no global, para evitar colisiones entre usuarios | **Aprobada** · aplicar en la fase 5 · ER actualizado |
| 12 | 2026-10-16 | Decisión (dominio) | Transiciones de estado. El asistente de desarrollo implementó transiciones estrictamente lineales (Registrado → Evaluado → Priorizado → Reparado). La tesis (HU-12) solo dice que el funcionario puede cambiar el estado a Evaluado, Priorizado o Reparado, y el diseño de Figma permite elegir cualquiera. Recomendación del asistente: permitir **avances con salto** (p. ej. Evaluado → Reparado), no permitir retrocesos, y registrar todo en el historial. **Decisión del responsable:** se permiten avances con salto y no retrocesos; si una cuadrilla repara un daño antes de formalizar la prioridad, no se obliga a pasar por Priorizado | **Aplicada** (2026-10-16) · commit `6a2c60c` · `reports/domain/status_machine.py` |
| 13 | 2026-10-16 | Decisión (dominio) | "Reporte activo" = todo estado distinto de Reparado (coincide con la deduplicación de la tesis); un reporte reparado conserva su última evaluación y no se recalcula | Confirmada |
| 14 | 2026-10-16 | Decisión (datos) | Pesos iniciales 0,50 / 0,30 / 0,20 insertados en la migración 0005 (no en un *seed*), porque el motor no evalúa sin ellos. Condiciones: (1) inserción repetible sin duplicar la fila; (2) índice único parcial sobre `vigente = true` para garantizar una sola configuración vigente; (3) `CHECK` de cada peso entre 0 y 1 y suma = 1,00 en la base de datos; (4) no editar la migración 0005 una vez aplicada: los cambios de valores por defecto van en una migración nueva y los ajustes normales (HU-14) son filas nuevas, nunca actualizaciones | **Aprobada con condiciones** · **Aplicada** (2026-10-16) · migración 0005 · `docs/base-de-datos.md` |
| 15 | 2026-10-16 | Corrección | Tabla de pruebas 8.3: Carrera 27 tiene P = 3,75 (d = 350 m), no 3,8; 3,8 era el redondeo a un decimal. Corregidas la guía y el texto de Figma; la tesis no repite el valor | Aplicada |
| 16 | 2026-10-16 | Corrección | El commit `ebc960d` (modelo U) cita `Refs: HU-05`; según la sección 2.6 debía ser **HU-03**. No se reescribe `main` (`push --force` prohibido); queda registrado aquí. Trazabilidad correcta de la fase 3: modelo U → HU-03 · motor de evaluación → HU-05 · máquina de estados → HU-12 · pesos versionados → HU-14 · pruebas del motor → HU-18 | Registrada |
| 17 | 2026-10-16 | Decisión menor | Distancias con `geometry` en SRID 4326 e índice GiST de expresión sobre `::geography` (`docs/adr/0003-distancias-geography.md`) | Aceptada |
| 18 | 2026-10-16 | Propuesta (ER) | `configuracion_pesos.id_usuario` permite `NULL`, que significa "configuración del sistema", porque la fila inicial se crea en una migración antes de que exista algún administrador; así se evita crear un usuario ficticio | **Aprobada** · **Aplicada** · columna opcional desde la migración 0002; la 0005 la usa para insertar la fila del sistema · ER actualizado en Lucid |
| 19 | 2026-10-16 | Decisión (versionado) | `AGENTS.md` es la fuente canónica de la guía y se versiona en git; `CLAUDE.md` es local (excluido de git) y solo importa `@AGENTS.md`, para tener una única copia y evitar que se desincronicen | **Aprobada** · **Aplicada** (2026-10-16) |
| 20 | 2026-10-16 | Propuesta (versionado) | Etiquetar cada cierre de fase con una etiqueta anotada SemVer (`v0.1.0` fase 1, `v0.2.0` fase 2, …) y mover lo de «Sin publicar» del `CHANGELOG.md` a cada versión. Las fases 1 a 3, ya cerradas, se etiquetan retroactivamente sobre el *merge* de cierre de cada una | **Aprobada** · **Aplicada** (2026-10-16) · etiquetas `v0.1.0` (`45f0097`), `v0.2.0` (`2c8f6f6`) y `v0.3.0` (merge de `chore/versionado`); `CHANGELOG.md` por versión |
| 21 | 2026-10-16 | Propuesta (seguridad / versionado) | Añadir `gitleaks` a `.pre-commit-config.yaml` y a la CI para detectar secretos en los commits; complementa `detect-private-key`, que solo cubre claves privadas | **Aprobada** · **Aplicada** (2026-10-16) · gitleaks v8.21.2 en `.pre-commit-config.yaml` y job `secrets` de la CI |
| 22 | 2026-10-16 | Propuesta (calidad / seguridad) | Integrar **SonarQube Cloud** como complemento del CI (análisis estático de seguridad y calidad, duplicación, tendencia de cobertura y puerta de calidad sobre el código nuevo). Pasos: (1) el responsable ya importó el repositorio y guardó el secreto `SONAR_TOKEN` en GitHub; (2) en una rama `chore/sonarcloud`: `sonar-project.properties`, informe de cobertura XML desde pytest (`--cov-report=xml`) y un job de análisis en `ci.yml` con acción de versión fija verificada, usando solo `SONAR_TOKEN` desde los secretos; (3) arrancar con la puerta de calidad estándar sobre el código nuevo, sin exigir arreglar todo lo previo; (4) corregir el disparador de `ci.yml` para que también corra al subir ramas de trabajo (hoy solo con push a `main`), de modo que el análisis y las pruebas avisen antes de integrar. Nunca imprimir ni versionar el token. Más adelante, añadir la cobertura y el análisis del panel (React) y de la app (Flutter) | **Aplicada** (2026-10-16) · rama `chore/sonarcloud` · `sonar-project.properties`, job `sonar` con `sonarqube-scan-action` v8.3.0 fijada por commit · requiere desactivar el *Automatic Analysis* en SonarQube Cloud |
| 23 | 2026-10-16 | Decisión (responsable) | Fase 4: (a) la supresión de datos se atiende **de inmediato**: en la misma transacción se anonimiza al titular, se revocan sus sesiones y la solicitud queda `atendida` con fecha; (b) los administradores se crean **solo por CLI** (`create-admin`, contraseña sin eco); (c) la versión de la política de datos es `1.0`, configurable con `PRIVACY_POLICY_VERSION` | **Aprobada** · (b) y (c) aplicadas (commit `76e27f2`) · (a) pendiente de aplicar |
| 24 | 2026-10-16 | Decisión menor | Autenticación: Argon2id (`argon2-cffi`), JWT HS256 (`PyJWT`), `email-validator`, contraseñas de 12 a 128 caracteres (OWASP ASVS V2.1), refresco opaco con SHA-256 y rotación con detección de reutilización, usuario y rol leídos de la base en cada petición (`docs/adr/0004-autenticacion.md`) | Aceptada · aplicada (commit `76e27f2`) |
| 25 | 2026-10-16 | Decisión menor | Límite de intentos: bloqueo por correo (exista o no la cuenta) tras 5 fallos seguidos, 1 → 2 → 4 → 8 → 15 min; límite por IP con ventana deslizante en login (30/5 min) y registro (10/h); 429 con `Retry-After`; contadores en memoria del proceso tras los puertos `RateLimiter` y `LoginAttemptStore`. Al poner el proxy HTTPS (HU-17) configurar `FORWARDED_ALLOW_IPS`; con varios procesos, pasar a PostgreSQL o Redis (`docs/adr/0005-limite-de-intentos.md`) | Aceptada · aplicada (commit `78cd7cc`) |

---

## 18. Referencias de buenas prácticas

- OWASP Top 10, OWASP ASVS, OWASP Mobile Top 10
- WCAG 2.2 (nivel AA)
- Twelve-Factor App
- Conventional Commits y Semantic Versioning
- Política de uso de Nominatim y de OpenStreetMap
- Ley Estatutaria 1581 de 2012 (protección de datos personales, Colombia)
- Documentación oficial de FastAPI, PostGIS, Flutter, React y Leaflet
