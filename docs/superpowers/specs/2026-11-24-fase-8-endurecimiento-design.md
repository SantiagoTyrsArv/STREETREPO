# Fase 8 — Endurecimiento para la sustentación

> Diseño · 2026-11-24 · guía, sección 13 (fase 8) · bitácora, fila 137

## 1. Intención

El responsable decidió que, por ahora, el sistema solo tiene que funcionar en su celular y en la
sustentación; el despliegue en servidor sigue pospuesto (fila 123). La fase 8 se enfoca en
**dejar evidencia verificable de calidad** que se pueda mostrar o citar en la tesis: seguridad,
rendimiento y accesibilidad, más las deudas pequeñas que encajan en esos tres frentes (opción 1,
elegida por el responsable el 2026-11-24).

**Éxito:** al cerrar la fase hay tres informes en `docs/` (seguridad, carga y accesibilidad) con
lo medido, lo corregido y lo que queda, todo respaldado por pruebas o comandos que se pueden
repetir; Sonar queda sin avisos abiertos; la CI sigue en verde y se etiqueta `v0.8.0`.

## 2. Objetivos, no objetivos y antiobjetivos

**Objetivos**
1. Revisión de seguridad contra la lista de la sección 15 de la guía, con correcciones.
2. Límite global de solicitudes por IP (decisión 30c).
3. Pruebas de carga con Locust (decisión 68) contra las metas de la guía 11.
4. Revisión de accesibilidad del panel (axe) y de la app (pautas de Flutter), con correcciones.
5. Sonar en cero avisos y el aviso de `starlette.testclient` resuelto (decisión 46e).

**No objetivos** (quedan para cuando haya servidor o para otra decisión)
- Programar `purge-orphan-photos`, respaldos y monitoreo.
- Sentry (decisión 67): el responsable decidió dejarlo fuera; sin servidor ni otras personas
  usando la app, los errores se ven en los logs locales y en `adb logcat`. Se retoma antes de la
  prueba en campo.
- Pruebas de punta a punta del panel en la CI (necesitan una base con datos de OSM).
- React 19 en la página (fila 136).

**Antiobjetivos** (harían fallar la fase aunque todo funcione)
- Presentar las cifras de carga como resultados de campo o del capítulo 4: son **medidas del
  sistema en un equipo local**, y el informe lo dice en su primera línea.
- Debilitar un límite de seguridad de forma permanente para que pase la prueba de carga: los
  ajustes solo existen en la configuración del entorno de carga.
- Romper la página publicada o cambiar textos o pantallas aprobadas para «cumplir» una
  herramienta automática sin que el responsable lo vea.

## 3. Restricciones

- Fecha: la prueba piloto vence el 2026-12-11 (ARE-41); la fase 8 no debe frenar las decisiones
  D1 a D7 de la guía de la prueba piloto, que siguen en manos del responsable.
- Stack fijo (guía 3). Locust ya está decidido (decisión 68); axe para Playwright es una
  decisión menor que se registra en la bitácora.
- Una rama por frente (guía 8.4), integrada por *merge* sin PR, con pruebas, lint y tipos.
- Sin datos personales en informes ni en logs; las cuentas de carga usan `@demo.invalid` o
  `@carga.invalid`.

## 4. Enfoques considerados

| Enfoque | Qué cubre | Por qué sí o no |
|---|---|---|
| **1. Evidencia para la sustentación (elegido)** | Seguridad, carga, accesibilidad y deudas pequeñas | Cada frente deja algo que se puede mostrar o citar |
| 2. Cerrar todas las deudas técnicas | Lo anterior más E2E en la CI | Más costo (datos OSM fijos en la CI) sin aporte visible en la sustentación |
| 3. Todo, incluido el servidor | Lo anterior más programación de tareas y respaldos | No sirve al objetivo actual y compite con el tiempo de la prueba piloto |

## 5. Diseño por frente

Orden de ejecución: primero lo que cambia el código (5.1 y 5.2), luego la revisión que lo
audita (5.3), luego accesibilidad (5.4) y al final la carga (5.5), que mide el estado definitivo.

### 5.1 Sonar en cero y aviso de Starlette — rama `refactor/backend-avisos-sonar`

Hoy hay 99 avisos (todos *code smells*; 0 errores, 0 vulnerabilidades, 0 *hotspots*):
S5778 (53, pruebas con más de una llamada dentro de `pytest.raises`), S8409 (32,
`response_model` redundante con la anotación de retorno), S7503 (4), S1192 (3, literales
repetidos en los modelos), S7632 (2, sintaxis de supresión), S5713 (2) y uno de S7492, S8997 y
S1135.

- Se corrigen todos sin cambiar el comportamiento: las pruebas existentes son la red.
- S8409: se quita `response_model` solo donde la anotación de retorno da el mismo esquema; se
  comprueba que el OpenAPI generado no cambie (comparar `openapi.json` antes y después).
- Aviso de Starlette: `TestClient` pide `httpx2`; el constructor elige entre instalarlo como
  dependencia de desarrollo o filtrar el aviso, según lo que diga la documentación de la
  versión instalada, y lo registra.

### 5.2 Límite global por IP — rama `feat/core-limite-global`

- Un *middleware* cuenta todas las solicitudes por IP con el `RateLimiter` que ya existe (en
  memoria, por proceso; la misma limitación documentada en el ADR 0004).
- Cupo **configurable** por variable de entorno (`GLOBAL_RATE_LIMIT_PER_IP`, con su ventana);
  valor propuesto: **600 solicitudes cada 5 minutos** (2 por segundo de media), holgado por el
  NAT de redes móviles y universidades y por las miniaturas que pide el panel.
- Fuera del cupo: `/health`, `/ready` y la documentación de la API.
- Respuesta: 429 con el formato de error uniforme, código `RATE_LIMITED` y `Retry-After`.
- Pruebas unitarias del *middleware* (cupo, exclusiones, cabecera) y una de integración.
- `.env.example` y el README documentan la variable.

### 5.3 Revisión de seguridad — rama `docs/seguridad-revision-fase-8`

- Se recorre cada punto de la sección 15 de la guía con su **evidencia**: archivo, prueba o
  comando que lo demuestra (p. ej. `pip-audit`, `npm audit`, la prueba de Argon2id, la de RBAC
  en `/admin`, la de EXIF eliminado).
- Además: `flutter pub outdated` y un repaso de las cabeceras de la API y del panel con el
  stack local levantado.
- Lo que falle se corrige en ramas `fix/…` aparte, con prueba que lo cubra.
- Producto: `docs/seguridad/revision-fase-8.md` con una tabla punto · estado · evidencia y una
  sección «Fuera de alcance» que liste lo que solo aplica con servidor (HTTPS real, proxy y
  respaldos), con remisión a la configuración ya integrada (fila 121).

### 5.4 Accesibilidad — ramas `test/admin-web-accesibilidad` y `test/mobile-accesibilidad`

**Panel**
- `@axe-core/playwright` en `admin-web/e2e/`: una prueba recorre inicio de sesión, Priorización,
  Detalle y estado, Pesos, Comparación (Zonas, Rondas y Resultados) y la vista del evaluador, y
  falla con hallazgos **serios o críticos** de WCAG 2.2 A/AA.
- Corre con el *script* de E2E que ya existe (`infra/scripts/e2e-panel.sh`), no en la CI.
- Se corrigen los hallazgos; los que no se puedan corregir sin cambiar el diseño aprobado se
  proponen con el protocolo 0.3 en vez de aplicarse.

**App**
- Pruebas de *widgets* con las pautas de Flutter (`androidTapTargetGuideline`,
  `iOSTapTargetGuideline`, `labeledTapTargetGuideline`, `textContrastGuideline`) en las
  pantallas del flujo crítico: bienvenida, inicio de sesión, registro, política, nuevo reporte
  (foto y severidad), posible duplicado, reporte enviado, mis reportes, detalle, mapa y perfil.
- Se corrigen los hallazgos con la misma regla del panel.

**Producto:** `docs/accesibilidad/revision-fase-8.md` con lo revisado, lo corregido y lo que
queda (incluida la revisión manual con TalkBack, que el responsable puede hacer en su celular
con una lista corta).

### 5.5 Pruebas de carga — rama `test/backend-carga-locust`

- `locust` como dependencia de desarrollo del backend; escenarios en `backend/loadtests/`.
- Escenarios (decisión 68 y guía 11):
  - ciudadano: `GET /reports` por área visible, `GET /reports/nearby` y `POST /reports` con una
    foto pequeña generada (incluye el cálculo de U en la misma transacción);
  - administrador: `GET /admin/ranking` y `GET /admin/heatmap`.
- Entorno: el stack de Docker Compose local con datos OSM de Pasto y `seed-demo`. Los cupos por
  usuario e IP se suben **solo** en ese entorno con variables de entorno (antiobjetivo 2), y
  las cuentas de carga, con sus reportes y fotos, se crean y se borran con un comando (como
  `seed-demo --remove`), para no dejar basura en la base local.
- Carga: rampa hasta 50 usuarios simultáneos durante unos minutos; se reportan p50, p95,
  máximo, solicitudes por segundo y errores por endpoint, comparados con las metas
  (listados < 500 ms; envío de reporte < 3 s).
- Producto: `docs/rendimiento/informe-carga-fase-8.md` con el equipo usado (CPU, RAM, sistema),
  la configuración exacta, el comando para repetirlo y las cifras, marcadas como medidas en
  local. Si una meta no se cumple, se registra tal cual y se propone la mejora (protocolo 0.3);
  no se ajusta la meta.

### 5.6 Cierre

README (variable del límite global, cómo correr carga y axe), CHANGELOG, versión `0.8.0` en
backend y panel, etiqueta `v0.8.0`, sección 13 de la guía, bitácora y Linear con capturas
(memoria de evidencia fotográfica).

## 6. Lo que queda al constructor

- Los nombres exactos de las variables de entorno y la ventana del límite global.
- Cómo resolver el aviso de Starlette (instalar `httpx2` o filtrar), según la documentación.
- El número de usuarios y la duración exactos de la carga, mientras cubran la meta de la guía.
- Qué pantallas de la app requieren datos falsos para la prueba de pautas.

## 7. Riesgos

- **El límite global corta la prueba de carga o las E2E:** se sube por variable solo en esos
  entornos; las pruebas lo cubren.
- **axe pide cambios de diseño** (p. ej. contraste de un color de marca): se proponen, no se
  aplican solos.
- **Las cifras de carga dependen del equipo:** el informe documenta el equipo y el comando, y
  no las presenta como resultados de campo.
