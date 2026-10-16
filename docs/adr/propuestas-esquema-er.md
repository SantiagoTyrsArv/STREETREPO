# Propuestas derivadas del diagrama ER (2026-10-15)

Detectadas al implementar la migración 0002. El esquema se implementó tal como está en el diagrama.

**Decisión (2026-10-15):** el responsable aprobó las seis propuestas con la recomendación indicada en cada una.
Cada una se implementa en su propia rama `improve/propuesta-NN-…` en la fase señalada.
Las propuestas 6, 8, 9 y 10 requieren actualizar el diagrama ER en Lucid; la 7 y la 10, el texto de la tesis
(regla del factor F y tratamiento de la supresión de datos).

## Propuesta 6 · Geometría de la vía

- **Dónde:** diagrama ER, entidad `via`.
- **Situación actual:** `via` tiene `osm_id`, `nombre`, `jerarquia_vial` y `factor_flujo`, pero no tiene geometría.
- **Mejora sugerida:** añadir `geom GEOMETRY(LineString, 4326)` (o `MultiLineString`) con índice GiST.
- **Justificación:** la guía (2.2, 3.1) exige asociar el reporte a la vía OSM más cercana dentro de 30 m
  y calcular F localmente en PostGIS. Sin la línea de la vía no hay forma de medir esa distancia.
- **Impacto:** una columna y un índice; bloquea la fase 2 (carga OSM y *map-matching*). Hay que actualizar el diagrama ER.
- **Recomendación:** aplicar antes de la fase 2.

## Propuesta 7 · Correspondencia `highway` → `jerarquia_vial`

- **Dónde:** diagrama ER (`via.jerarquia_vial`) y regla de F en la tesis/guía 2.2.
- **Situación actual:** el ENUM tiene primaria, secundaria, terciaria y residencial. La regla de F menciona además
  `unclassified` y `service` (F = 2), y no dice qué hacer con `trunk` ni con los `*_link`. Las vías nacionales
  (como la Panamericana) se suelen etiquetar `trunk` en OSM. **Comprobado en la primera carga (2026-10-15):**
  19 de los 61 tramos con nombre Panamericana están etiquetados `trunk`/`trunk_link`.
- **Mejora sugerida:** fijar la correspondencia: `trunk`, `primary` (y sus `_link`) → primaria;
  `secondary` → secundaria; `tertiary` → terciaria; `residential`, `unclassified`, `service`, `living_street` → residencial.
  El resto de etiquetas (`footway`, `track`, etc.) no se cargan.
- **Justificación:** sin esta regla una vía troncal quedaría fuera del modelo o con F = 2, lo que subestima la urgencia.
- **Impacto:** solo el script de carga; la tesis debería explicitar la regla en la sección del factor F.
- **Recomendación:** aplicar en la fase 2.

## Propuesta 8 · Versión de la política de datos

- **Dónde:** diagrama ER, entidad `usuario`.
- **Situación actual:** se guarda `acepta_politica` y `fecha_aceptacion`, no la versión aceptada.
- **Mejora sugerida:** añadir `version_politica VARCHAR(20)`.
- **Justificación:** la guía 7.2 pide registrar fecha **y versión**; si la política cambia hay que saber qué aceptó cada titular (Ley 1581, deber de prueba de la autorización).
- **Impacto:** una columna; afecta el registro (fase 4).
- **Recomendación:** aplicar en la fase 4.

## Propuesta 9 · Tokens de refresco revocables

- **Dónde:** diagrama ER (no existe la entidad).
- **Situación actual:** no hay dónde guardar tokens de refresco.
- **Mejora sugerida:** tabla `token_refresco` (id, id_usuario, hash del token, emitido, expira, revocado, reemplazado_por).
- **Justificación:** la guía 7.1 pide refresco rotatorio y revocable; un JWT de refresco sin estado no se puede revocar ni detectar su reutilización (OWASP ASVS V3).
- **Impacto:** una tabla; fase 4.
- **Recomendación:** aplicar en la fase 4.

## Propuesta 10 · Supresión por anonimización

- **Dónde:** diagrama ER (`reporte.id_usuario`) y flujo de supresión (guía 7.2).
- **Situación actual:** `reporte.id_usuario` es obligatorio y se implementó con `RESTRICT`: un usuario con reportes no se puede borrar.
- **Mejora sugerida:** atender la supresión anonimizando al titular (borrar nombre, correo y hash; desactivar la cuenta)
  y conservar sus reportes como dato de la vía. Opcionalmente, una tabla `solicitud_supresion` para el trámite.
- **Justificación:** la Ley 1581 obliga a suprimir los datos personales, pero el daño vial reportado no es un dato personal
  y es útil para la Secretaría; borrar en cascada eliminaría evidencia de otros usuarios (confirmaciones, historial).
- **Impacto:** reglas de la fase 4/5; la tesis debería describir el tratamiento de la supresión.
- **Recomendación:** aplicar en la fase 4.

## Propuesta 11 · Idempotencia en la creación de reportes

- **Dónde:** diagrama ER (`reporte`) y guía 6.1 / 10.3.
- **Situación actual:** no hay columna para una clave de idempotencia.
- **Mejora sugerida:** `clave_idempotencia UUID UNIQUE` (nullable) en `reporte`, enviada por la app en la cabecera `Idempotency-Key`.
- **Justificación:** con red móvil inestable un reintento puede crear el mismo reporte dos veces (patrón de las APIs de pago, p. ej. Stripe).
- **Impacto:** una columna y un índice único; fase 5.
- **Recomendación:** aplicar en la fase 5.
