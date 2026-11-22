# Objetivo 4 de la tesis: comparación del ranking con el panel de referencia (HU-09)

Fecha: 2026-11-22 · Estado: diseño para aprobación · Rama: `docs/objetivo-4-diseno`
Fuentes: tesis `CTG_Noviembre_SantiagoArevalo.docx` (2.3, 3.4 a 3.8, 4.4), Linear ARE-22 y ARE-41,
bitácora (decisiones 3, 47 y 76; propuesta 114 de esta sesión), Figma «Panel · Comparación con el
panel de referencia».

## 1. Intención

La tesis contrasta tres hipótesis (2.3): el motor de priorización produce un ranking más objetivo
que el criterio manual (Hi), no hay diferencia (H0), o la diferencia depende del volumen de reportes
de la zona (Ha). Para eso, un panel de 2 a 3 personas ordena **a ciegas** los mismos reportes de
2 a 3 zonas de Pasto (al menos una de alta y una de baja concentración de reportes) y se compara su
orden con el del motor.

Este trabajo construye la **herramienta** de esa comparación dentro del sistema: zonas, rondas de
evaluación con los reportes congelados, la vista a ciegas para los evaluadores, el cálculo del
acuerdo y la exportación de la ficha comparativa. **No** ejecuta la prueba piloto ni produce
resultados: el capítulo 4 sigue en pausa hasta que haya reportes reales y un panel definido.

## 2. Metas, no metas y anti-metas

**Metas**
- Cargar las zonas de la prueba piloto desde un GeoJSON y ver cuántos reportes tiene cada una.
- Abrir una ronda que congele los reportes de cada zona con su U y el orden del motor.
- Que cada evaluador ordene los reportes de cada zona sin ver nada del motor.
- Calcular por zona el acuerdo motor–panel y entre evaluadores, y la comparación entre zonas.
- Exportar la ficha comparativa de la sección 4.4 (CSV) para la tesis.

**No metas**
- Elegir a los evaluadores (el responsable lo decide después; el sistema solo da cuentas «evaluador»).
- Editar zonas en el panel (se cargan por línea de comandos).
- Declarar en el sistema qué hipótesis se acepta: el sistema da estadísticos y valores p; la
  interpretación va en la tesis.
- Hacer dentro del panel la revisión manual de duplicados (se hace sobre una exportación; el sistema
  sí registra sus avisos, ver 8.1).
- Datos de demostración para la comparación (ver 9).

**Anti-metas** (sería un fracaso aunque funcione)
- Que el evaluador pueda ver, deducir o pedir a la API la U, S, F, P, el orden del motor, las
  confirmaciones o el orden de otro evaluador.
- Que una ronda cambie después de abierta (nuevos reportes, nuevos pesos o recálculos), lo que
  haría irreproducible la comparación.
- Presentar como resultados de la tesis números calculados con datos de prueba o de demostración.

## 3. Decisiones del responsable

1. **Enfoque 1:** todo dentro del sistema (backend + panel), no un análisis aparte.
2. **Vista a ciegas dentro del panel web** (opción A), con cuentas de rol **evaluador**; quiénes
   serán se decide después.
3. **Zonas por GeoJSON** cargado con un comando, como `osm-import` (opción C).
4. **Registrar los avisos de «Posible duplicado»** y la decisión del ciudadano (sección 8.1), para
   poder medir la deduplicación que promete la tesis.
5. **Propuesta 114, aprobada:** el acuerdo se mide con **rho de Spearman** y **tau de Kendall** por
   zona (motor frente a panel), **W de Kendall** entre evaluadores, y una **coincidencia dentro de
   ±1 posición** como dato descriptivo. Entre zonas, **U de Mann-Whitney** (dos zonas) o
   **Kruskal-Wallis** (tres) sobre el desacuerdo por reporte, con α = 0,05. Reemplaza al
   «porcentaje de coincidencia» de posición exacta.

## 4. Enfoques considerados

| Enfoque | Qué es | A favor | En contra |
|---|---|---|---|
| **1. Todo en el sistema (elegido)** | Módulo `validation` en el backend, tres pantallas en el panel, estadísticas con `scipy` | Reproducible, probado, visible en vivo ante el jurado; usa la pantalla del Figma | El más grande: migración, rol nuevo, cambio del ER |
| 2. Órdenes en el sistema, análisis aparte | Igual, sin pantalla de Comparación; CSV y notebook en `docs/` | Menos código en el panel | La pantalla del Figma queda sin construir; el resultado no se ve en el sistema |
| 3. App aparte para evaluadores | Vista a ciegas fuera del panel | — | Duplica autenticación y sesión; descartado |

## 5. Flujo

1. **Zonas.** `python -m app.cli zones-import zonas.geojson` carga los polígonos (2 o 3) con
   `name` y `concentration` (`alta` | `baja`) en sus propiedades. Es idempotente por nombre:
   volver a cargar reemplaza la geometría. Al cargar, asigna `reporte.id_zona` a los reportes que
   caen dentro (`ST_Covers`); los reportes nuevos reciben su zona al crearse. Un reporte fuera de
   toda zona queda con `id_zona` NULL. Los polígonos no deben solaparse (se rechaza el archivo).
   *El GeoJSON de la prueba se versiona en `docs/validacion/zonas.geojson` cuando exista.*
2. **Ronda.** El administrador abre una ronda en el panel con un nombre y un **tamaño de muestra
   por zona** (n). El sistema toma los reportes **activos** (todo estado salvo Reparado) de cada
   zona; si una zona tiene más de n, elige n al azar con una **semilla guardada** en la ronda, para
   que se pueda reproducir. Por cada reporte guarda una foto fija: U vigente, versión de pesos y
   **orden del motor** dentro de su zona, según `priority/domain/ranking.py` (U, severidad,
   confirmaciones, antigüedad). Una zona con menos de `MIN_REPORTS_PER_ZONE` (5) reportes no puede
   entrar a la ronda.
3. **Evaluación a ciegas.** Cada evaluador ve sus zonas pendientes. En cada zona ordena las tarjetas
   de más a menos urgente y envía. **Enviar es definitivo** para esa zona y ese evaluador.
4. **Cierre.** El administrador ve el avance (qué evaluador envió qué zona) pero **no** las métricas
   mientras la ronda está abierta: así no influye en el panel. Al cerrar la ronda ya no se aceptan
   órdenes y se calculan las métricas.
5. **Comparación.** Pantalla con las métricas por zona y entre zonas, y exportación de la ficha.

Solo puede haber **una ronda abierta** a la vez (mi decisión: simplifica el flujo del evaluador).

Casos de borde (mis decisiones):
- Una zona con menos de n reportes, pero al menos el mínimo, entra con todos los que tiene.
- Si un reporte cambia de estado, se repara o su autor pide la supresión durante la ronda, sigue en
  la ronda con su foto fija; si la foto ya no existe, la tarjeta dice «Foto no disponible».
- Al cerrar, un evaluador que no envió una zona no cuenta en esa zona. Una zona sin ningún orden
  enviado aparece como «Sin órdenes» y no entra a la comparación entre zonas.
- La prueba entre zonas exige al menos una zona `alta` y una `baja` con órdenes; si no, se indica
  por qué no se calcula.

## 6. Qué ve el evaluador (vista a ciegas)

Por tarjeta: foto (miniatura y ampliada), descripción, nombre de la vía, severidad declarada por el
ciudadano y un minimapa con el punto y los servicios críticos a menos de 500 m. Las tarjetas se
muestran en un **orden inicial aleatorio**, distinto por evaluador, para no sugerir ninguno.

No ve: U, S, F, P, jerarquía vial, distancia calculada al servicio, confirmaciones, estado, fecha,
autor, el orden del motor ni el de otros evaluadores. La API del evaluador **no devuelve** esos
campos (no basta con ocultarlos en la interfaz).

```
Ronda «Piloto 1» · Zona Centro · 12 reportes             1 de 2 zonas
┌────┬─────────┬─────────────────────────────────────┬──────────┐
│ 1  │ [foto]  │ Carrera 27 · Severidad alta         │  ▲  ▼  ⠿ │
│ 2  │ [foto]  │ Calle 18 · Severidad media          │  ▲  ▼  ⠿ │
│ …  │         │                                     │          │
└────┴─────────┴─────────────────────────────────────┴──────────┘
                     [Ver en el mapa]      [Enviar este orden]
```

Ordenar se hace arrastrando **y** con botones subir/bajar (teclado y lector de pantalla, WCAG 2.2
AA). Enviar pide confirmación («No podrás cambiarlo»). El orden en curso se guarda en el navegador
(`sessionStorage`) para no perderlo al recargar; no se envía hasta pulsar «Enviar».

## 7. Métricas (propuesta 114)

Para cada zona de una ronda cerrada:
- **Orden del panel (consenso):** posición media de cada reporte entre los evaluadores que enviaron,
  convertida a rangos; los empates quedan como rangos promedio (`scipy.stats.rankdata`, método
  `average`), sin desempatar con el motor. *Mi decisión: rangos promedio, el estándar.*
- **rho de Spearman** y **tau-b de Kendall** entre el orden del motor y el del panel, con su valor p.
  También por evaluador individual.
- **W de Kendall** entre evaluadores (con 2 o más), con su prueba chi-cuadrado.
- **Coincidencia ±1:** porcentaje de reportes cuyo orden del panel está a una posición o menos del
  del motor. Descriptiva.

Entre zonas:
- **Desacuerdo por reporte:** |orden motor − orden panel| / (n − 1), en [0, 1], para comparar zonas
  de distinto tamaño.
- Dos zonas: **U de Mann-Whitney** (bilateral) entre los desacuerdos de la zona de alta y la de baja.
  Tres zonas: **Kruskal-Wallis**. Se informa estadístico, p y «diferencia significativa con
  α = 0,05: sí/no».

Las métricas se calculan en el dominio con funciones puras sobre los datos de la ronda y se prueban
con casos conocidos (rankings idénticos → rho = 1; invertidos → −1; ejemplos con valores de
referencia de `scipy`). α = 0,05 y `MIN_REPORTS_PER_ZONE` son constantes con nombre. Con un solo
evaluador, W no se calcula y se indica.

## 8. Ficha comparativa (exportación)

CSV por ronda, una fila por reporte, con las columnas de la sección 4.4 más el detalle:
`id_reporte, zona, concentracion, puntaje_u, orden_motor, orden_panel, desacuerdo, coincide_pm1,
orden_evaluador_1 … orden_evaluador_k`. Los evaluadores aparecen como «Evaluador 1, 2…», no por
nombre ni correo (minimización, Ley 1581). Un segundo CSV resume las métricas por zona y entre
zonas. Decimales con punto en el CSV (para análisis), con coma en la pantalla.

Para la parte de deduplicación del objetivo 4, la pantalla y el CSV de resumen dan por zona:
reportes, reportes con al menos una confirmación, total de confirmaciones y los avisos de duplicado
con su decisión (8.1). La revisión manual se hace sobre dos CSV más: los reportes de cada zona (id,
fecha, vía, enlace a la foto para el administrador) y los avisos de cada zona (candidatos, decisión
y reporte resultante), donde el revisor marca si era de verdad el mismo daño.

### 8.1 Registro de avisos de duplicado (decisión 4)

- **Cuándo se registra:** cada vez que el servidor ofrece candidatos a un ciudadano, en
  `GET /reports/nearby` con resultados y en el 409 `REPORT_DUPLICATE_NEARBY` de `POST /reports`. La
  respuesta incluye un `duplicate_warning_id`.
- **Qué guarda:** usuario, fecha, zona del punto consultado (no el punto exacto: minimización), los
  reportes candidatos y su distancia, y la **decisión**: `pendiente` al crearse; `confirmo` (y qué
  reporte) si el ciudadano confirma uno de los candidatos; `creo_igual` (y el reporte nuevo) si crea
  el suyo con `create_anyway`.
- **Cómo se enlaza:** la app manda el `duplicate_warning_id` al confirmar desde «Posible duplicado»
  o al crear con `create_anyway` (campo opcional; sin él, la acción funciona igual y el aviso queda
  `pendiente`). El servidor solo acepta el id de un aviso del mismo usuario y aún `pendiente`.
- Un aviso que sigue `pendiente` al exportar se informa como «sin decisión» (el ciudadano abandonó).
- Mide desde que se active: los avisos anteriores no existen y se dice así en la tesis.

## 9. Modelo de datos (migración 0009)

- `rol_usuario` gana el valor `evaluador`.
- `zona`: añade `concentracion` (ENUM `alta`, `baja`, NOT NULL) y `nombre` único. La geometría ya
  existe (`Polygon, 4326`, índice GiST).
- `ronda_evaluacion`: `id_ronda`, `nombre`, `estado` (`abierta`, `cerrada`), `tamano_muestra`,
  `semilla`, `id_config` (versión de pesos vigente al abrir), `id_usuario` (quién la abrió),
  `fecha_apertura`, `fecha_cierre`. Índice único parcial: una sola abierta.
- `ronda_reporte`: `id_ronda`, `id_reporte`, `id_zona`, `puntaje_u`, `orden_motor`; únicos
  (ronda, reporte) y (ronda, zona, orden_motor).
- `orden_evaluador`: `id_ronda`, `id_usuario`, `id_reporte`, `posicion`, `fecha_envio`; únicos
  (ronda, usuario, reporte) y (ronda, usuario, zona, posición). La zona se toma de `ronda_reporte`.

- `aviso_duplicado`: `id_aviso`, `id_usuario`, `id_zona` (NULL si fuera de toda zona), `fecha`,
  `decision` (ENUM `pendiente`, `confirmo`, `creo_igual`), `id_reporte_resultante` (el confirmado o
  el creado; NULL si pendiente).
- `aviso_duplicado_candidato`: `id_aviso`, `id_reporte`, `distancia_m` NUMERIC(6,2); único (aviso,
  reporte).

Se borra en cascada desde la ronda; un reporte no se borra mientras esté en una ronda (`RESTRICT`).
La supresión de datos de un evaluador anonimiza su cuenta, pero conserva sus órdenes (como ya pasa
con las confirmaciones). Hay que actualizar el ER de Lucid (el conector solo tiene lectura).

## 10. API (`/api/v1`)

Administrador (`require_admin`):
- `GET /admin/zones`: zonas con concentración, reportes activos y geometría simplificada.
- `POST /admin/evaluation-rounds` (`name`, `sample_size`) → 201; 409 si ya hay una abierta; 422 si
  una zona no llega al mínimo (el detalle dice cuál).
- `GET /admin/evaluation-rounds` y `GET /admin/evaluation-rounds/{id}`: avance por evaluador y zona.
- `POST /admin/evaluation-rounds/{id}/close` → 200; 409 si ya estaba cerrada.
- `GET /admin/evaluation-rounds/{id}/results`: métricas; 409 `ROUND_STILL_OPEN` si está abierta.
- `GET /admin/evaluation-rounds/{id}/export/{ficha|resumen|reportes|avisos}.csv`.

Cambios en rutas existentes (8.1): `GET /reports/nearby` y el 409 de `POST /reports` devuelven
`duplicate_warning_id`; `POST /reports` (campo de formulario) y
`POST /reports/{id}/confirmations` (cuerpo) aceptan `duplicate_warning_id` opcional. La app lo
guarda en el borrador y lo envía.

Evaluador (`require_evaluator`):
- `GET /evaluation/current`: la ronda abierta con sus zonas y si ya envió cada una.
- `GET /evaluation/current/zones/{id_zona}`: tarjetas a ciegas en orden aleatorio por evaluador.
- `GET /evaluation/current/reports/{id}/photo` y `/thumbnail`: solo reportes de la ronda abierta.
- `PUT /evaluation/current/zones/{id_zona}/order` (`report_ids` en orden) → 201; 409 si ya envió;
  422 si la lista no es exactamente el conjunto de la zona.

Cuentas: `python -m app.cli create-evaluator --name … --email …`, igual que `create-admin`. El
inicio de sesión web (`/auth/web/login`, decisión 42) acepta administrador **o** evaluador; cada
ruta sigue verificando su rol. Un evaluador **no** puede crear ni confirmar reportes (403), para
no contaminar los datos que evalúa.

## 11. Panel web

- **Administrador:** ítem «Comparación» del menú (Figma). Tres vistas: *Zonas* (mapa con los
  polígonos y conteos), *Rondas* (abrir, avance, cerrar) y *Comparación* (métricas por zona y entre
  zonas, como en el Figma, con botones de exportación). Seguir el Figma «Panel · Comparación con el
  panel de referencia» y los tokens de la guía 10.1.
- **Evaluador:** al iniciar sesión va a «Mis evaluaciones» (lista de zonas pendientes y enviadas) y
  a la vista a ciegas. No ve el menú del administrador; las rutas se protegen por rol.
- Estados de carga, vacío («No hay una ronda abierta»), error y éxito en cada vista.

## 12. Ajustes a la tesis (con la propuesta 114)

Al terminar la implementación: en 2.3 (nota), 3.4 (criterio de la HU-09), 3.7 y 4.4, cambiar
«porcentaje de coincidencia» por las medidas de la sección 7, añadir las columnas nuevas a la ficha
y explicar la ronda congelada y la vista a ciegas. Registrar en la bitácora.

## 13. Restricciones

- Guía `AGENTS.md`: monolito modular, capas, pruebas en cada fase (cobertura ≥ 80 % en dominio y
  aplicación), consultas parametrizadas, error uniforme, RBAC en servidor, sin datos personales en
  logs ni exportaciones.
- `scipy` es dependencia nueva del backend (decisión menor; fijar versión y auditar).
- Plazo: ARE-41 vence el 2026-12-11.

## 14. Lo que queda al constructor

Nombres de módulos y componentes, la librería de arrastrar y soltar del panel (accesible), la
simplificación de geometrías para el mapa, el formato exacto de los mensajes y la organización de
las pruebas, siempre dentro de lo anterior.
