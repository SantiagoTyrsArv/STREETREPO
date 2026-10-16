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
| — | 2026-10-15 | Decisión menor | [Distancias con `geometry` 4326 + índice `geography`](0003-distancias-geography.md) | Aceptada |
| 6 | 2026-10-15 | Propuesta | Añadir geometría (`LineString`) a `via` para el *map-matching* a 30 m | Aprobada (2026-10-15) · aplicar antes de la fase 2 |
| 7 | 2026-10-15 | Propuesta | Correspondencia `highway` de OSM → `jerarquia_vial` (incluye `trunk`, `unclassified`, `service`) | Aprobada (2026-10-15) · aplicar en la fase 2 |
| 8 | 2026-10-15 | Propuesta | Guardar la versión de la política aceptada en `usuario` (Ley 1581) | Aprobada (2026-10-15) · aplicar en la fase 4 |
| 9 | 2026-10-15 | Propuesta | Tabla de tokens de refresco revocables (guía 7.1) | Aprobada (2026-10-15) · aplicar en la fase 4 |
| 10 | 2026-10-15 | Propuesta | Supresión de datos por anonimización en lugar de borrado del usuario | Aprobada (2026-10-15) · aplicar en la fase 4 |
| 11 | 2026-10-15 | Propuesta | Clave de idempotencia en la creación de reportes (guía 6.1) | Aprobada (2026-10-15) · aplicar en la fase 5 |

El detalle de las propuestas 6–11 está en [propuestas-esquema-er.md](propuestas-esquema-er.md).
