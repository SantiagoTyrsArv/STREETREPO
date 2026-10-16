# Bitácora de decisiones y propuestas

Una decisión por archivo (`NNNN-titulo.md`). Las propuestas de mejora siguen el formato del
protocolo de desviaciones y solo se implementan tras su aprobación. Las propuestas pendientes
dejan un `TODO(propuesta-N)` en el código.

| # | Fecha | Tipo | Descripción | Estado |
|---|---|---|---|---|
| 1 | — | Decisión menor | Gestor de estado en Flutter (Riverpod / Bloc) | Pendiente |
| 2 | 2026-10-15 | Decisión menor | [Herramientas del backend](0002-herramientas-backend.md): SQLAlchemy 2 + GeoAlchemy2 + psycopg 3, uv, Python 3.13 | Aceptada |
| 3 | — | Propuesta | Diseñar pantallas faltantes: carga de datos OSM (HU-13) y comparación con expertos (HU-09) | Pendiente |
| 4 | — | Propuesta | Diseñar estados vacío, carga, error y sin conexión de cada pantalla | Pendiente |
| 5 | — | Propuesta | Documentar en la tesis los límites de uso de Nominatim, Overpass y *tiles* de OSM | Pendiente |
| 6 | 2026-10-15 | Propuesta | Añadir geometría (`LineString`) a `via` para el *map-matching* a 30 m | Aplicada (2026-10-15) · migración 0003 |
| 7 | 2026-10-15 | Propuesta | Correspondencia `highway` de OSM → `jerarquia_vial` (incluye `trunk`, `unclassified`, `service`) | Aplicada (2026-10-15) · `roads/domain/classification.py`, migración 0004 |
| 8 | 2026-10-15 | Propuesta | Guardar la versión de la política aceptada en `usuario` (Ley 1581) | Aprobada (2026-10-15) · aplicar en la fase 4 |
| 9 | 2026-10-15 | Propuesta | Tabla de tokens de refresco revocables (guía 7.1) | Aprobada (2026-10-15) · aplicar en la fase 4 |
| 10 | 2026-10-15 | Propuesta | Supresión de datos por anonimización en lugar de borrado del usuario | Aprobada (2026-10-15) · aplicar en la fase 4 |
| 11 | 2026-10-15 | Propuesta | Clave de idempotencia en la creación de reportes (guía 6.1); única por par (usuario, clave), no global | Aprobada (2026-10-15) · aplicar en la fase 5 |
| 12 | 2026-10-16 | Decisión (dominio) | Transiciones de estado: avances con salto permitidos (p. ej. Evaluado → Reparado) y retrocesos prohibidos; un reporte registrado solo lo evalúa el motor; todo cambio queda en el historial | Aplicada (2026-10-16) · `reports/domain/status_machine.py` |
| 13 | 2026-10-16 | Decisión (dominio) | "Reporte activo" = todo estado distinto de Reparado; un reporte reparado conserva su última evaluación y no se recalcula | Confirmada |
| 14 | 2026-10-16 | Decisión (datos) | Pesos iniciales 0,50 / 0,30 / 0,20 insertados por la migración 0005 (no en un *seed*), porque el motor no evalúa sin ellos; una sola configuración vigente | Recomendada aceptar · aplicada en la migración 0005 |
| 15 | 2026-10-16 | Corrección | Tabla de pruebas de la guía: Carrera 27 tiene P = 3,75 (d = 350 m), no 3,8 (redondeo a un decimal). Corregidas la guía y el texto de Figma; la tesis no repite el valor | Aplicada |
| 16 | 2026-10-16 | Corrección | El commit `ebc960d` (modelo U) cita `Refs: HU-05`; debía ser HU-03. No se reescribe `main`. Trazabilidad de la fase 3: modelo U → HU-03 · motor de evaluación → HU-05 · máquina de estados → HU-12 · pesos versionados → HU-14 · pruebas del motor → HU-18 | Registrada |
| 17 | 2026-10-15 | Decisión menor | [Distancias con `geometry` 4326 + índice `geography`](0003-distancias-geography.md) | Aceptada |

El detalle de las propuestas 6–11 está en [propuestas-esquema-er.md](propuestas-esquema-er.md).
