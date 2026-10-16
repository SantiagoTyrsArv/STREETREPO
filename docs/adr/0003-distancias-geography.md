# 0003 · Medición de distancias: `geometry` 4326 + índice `geography`

- **Fecha:** 2026-10-15
- **Tipo:** decisión menor (resuelve el punto abierto de la guía 5)
- **Estado:** aceptada

## Contexto

La guía pide guardar en SRID 4326 y elegir entre el tipo `geography` o una proyección métrica
para medir distancias (25 m, 30 m, 100–500 m). El diagrama ER, que tiene prioridad sobre la guía,
define las columnas como `GEOMETRY(Point, 4326)` y `GEOMETRY(Polygon, 4326)`.

## Decisión

- Las columnas se mantienen como **`geometry` en SRID 4326**, tal como dice el diagrama ER.
- Las distancias en metros se calculan con un **cast a `geography`**:
  `ST_DWithin(ubicacion::geography, punto::geography, 25)`.
- Cada columna de puntos tiene **dos índices GiST**: uno sobre `geometry` (consultas por *bounding box*
  del mapa, `ST_Contains` con zonas) y otro de expresión sobre `(ubicacion::geography)` para que los
  filtros por distancia usen índice. Una prueba de integración verifica con `EXPLAIN` que se usa.

## Alternativas descartadas

- **Columnas `geography`:** contradice el diagrama ER.
- **Proyección métrica (MAGNA-SIRGAS / Origen Nacional, EPSG:9377):** distancias exactas, pero exige
  `ST_Transform` en cada consulta y un índice por proyección; a la escala de Pasto `geography`
  da metros precisos sin depender de una proyección.

## Consecuencias

- Las consultas espaciales del repositorio deben usar siempre el cast `::geography` para radios en metros;
  se centralizarán en la capa de infraestructura con los radios como constantes con nombre (guía 2.3).
