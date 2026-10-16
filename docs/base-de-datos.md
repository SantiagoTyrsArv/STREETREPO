# Base de datos

Fuente: diagrama ER en Lucid ("Street Repo - Diagrama Entidad-Relación"). Migración:
`backend/migrations/versions/` (0002 esquema inicial, 0003 geometría de `via`, 0004 `via.highway_osm`, 0005 pesos iniciales).

Las tablas y columnas usan los nombres del diagrama (español). El código usa nombres en inglés
(guía 9.1); este es el mapeo.

## Tablas y modelos

| Tabla (ER) | Modelo ORM | Módulo |
|---|---|---|
| `usuario` | `UserModel` | `users` |
| `reporte` | `ReportModel` | `reports` |
| `evidencia` | `EvidenceModel` | `reports` |
| `historial_estado` | `StatusHistoryModel` | `reports` |
| `confirmacion` | `ConfirmationModel` | `confirmations` |
| `configuracion_pesos` | `WeightConfigModel` | `priority` |
| `evaluacion_prioridad` | `PriorityEvaluationModel` | `priority` |
| `via` | `RoadModel` | `roads` |
| `zona` | `ZoneModel` | `roads` |
| `servicio_critico` | `CriticalServiceModel` | `critical_services` |

## Columnas con nombre distinto en el código

| Columna (ER) | Atributo | Columna (ER) | Atributo |
|---|---|---|---|
| `id_<tabla>` (PK) | `id` | `id_usuario`, `id_reporte`… (FK) | `user_id`, `report_id`… |
| `nombre` | `name` | `correo` | `email` |
| `rol` | `role` | `activo` | `is_active` |
| `acepta_politica` | `accepted_policy` | `fecha_aceptacion` | `accepted_policy_at` |
| `fecha_registro` | `registered_at` | `ubicacion` | `location` |
| `direccion` | `address` | `severidad` | `severity` |
| `descripcion` | `description` | `estado` | `status` |
| `puntaje_prioridad` | `priority_score` | `fecha_creacion` | `created_at` |
| `url_foto` | `photo_url` | `formato` | `file_format` |
| `tamano_bytes` | `size_bytes` | `fecha_subida` | `uploaded_at` |
| `estado_anterior` / `estado_nuevo` | `previous_status` / `new_status` | `observacion` | `note` |
| `fecha_cambio` | `changed_at` | `fecha` (confirmación) | `confirmed_at` |
| `w_severidad` / `w_flujo` / `w_proximidad` | `severity_weight` / `flow_weight` / `proximity_weight` | `vigente` | `is_current` |
| `distancia_servicio_m` | `service_distance_m` | `s_severidad` / `f_flujo` / `p_proximidad` | `severity_score` / `flow_score` / `proximity_score` |
| `u_utilidad` | `urgency_score` | `fecha_calculo` | `calculated_at` |
| `jerarquia_vial` | `road_class` | `factor_flujo` | `flow_factor` |
| `tipo` | `service_type` | `geom` | `geom` |
| `highway_osm` | `highway_tag` | | |

## Tipos ENUM

| Tipo PostgreSQL | Valores (ER) | Enum de dominio |
|---|---|---|
| `rol_usuario` | ciudadano, administrador | `UserRole` |
| `estado_reporte` | registrado, evaluado, priorizado, reparado | `ReportStatus` |
| `jerarquia_vial` | primaria, secundaria, terciaria, residencial | `RoadClass` |
| `tipo_servicio` | hospital, escuela | `CriticalServiceType` |

`historial_estado.estado_anterior` y `estado_nuevo` (ENUM sin valores en el diagrama) usan `estado_reporte`.

## Decisiones de implementación

El diagrama no define nulabilidad, valores por defecto ni reglas de borrado. Se eligieron así:

| Punto | Decisión | Motivo |
|---|---|---|
| `reporte.severidad` | Código 1 = baja, 2 = media, 3 = alta (`CHECK 1..3`) | La normalización a S (3/6/10) vive en el dominio y puede ajustarse sin migrar datos |
| `reporte.id_via` | Opcional | NULL = sin vía a 30 m: F = 2 y "Revisar vía" (guía 2.2) |
| `reporte.id_zona`, `direccion` | Opcionales | El punto puede no caer en una zona; Nominatim puede no responder |
| `reporte.puntaje_prioridad` | Opcional, `CHECK 0..10` | Copia de la U vigente para ordenar el ranking; NULL hasta la primera evaluación |
| `historial_estado.id_usuario` | Opcional | NULL = transición automática del motor (Registrado → Evaluado) |
| `historial_estado.estado_anterior` | Opcional | NULL en el registro inicial |
| `configuracion_pesos` | `CHECK` rango 0–1 y suma = 1,00; índice único parcial sobre `vigente` | Pesos válidos y una sola versión vigente (guía 2.2, 4.5) |
| `configuracion_pesos.id_usuario` | Opcional | Configuración inicial cargada por el sistema |
| `evaluacion_prioridad.id_servicio`, `distancia_servicio_m` | Opcionales | Ningún servicio crítico a menos de 500 m (P = 0) |
| `via.nombre`, `servicio_critico.nombre` | Opcionales | Muchos elementos de OSM no tienen nombre |
| `usuario` | `CHECK`: si `acepta_politica` entonces `fecha_aceptacion` no nula | Consentimiento registrado (Ley 1581) |
| `usuario.correo` | `UNIQUE` (ER); la aplicación lo guarda en minúsculas | Evitar duplicados por mayúsculas |
| Borrado de un reporte | `CASCADE` en evidencia, confirmaciones, historial y evaluaciones | Son parte del reporte |
| Borrado de un usuario con reportes | `RESTRICT` | Ver propuesta 10 (supresión con anonimización) |
| Borrado de vía, zona o servicio | `SET NULL` | Una recarga de OSM no debe borrar reportes ni evaluaciones |
| Claves UUID | `gen_random_uuid()` en la base | Disponible en PostgreSQL ≥ 13 sin extensiones |
| `servicio_critico.osm_id` | Nodos con su id; áreas (vías de OSM) con el id en negativo | Nodos y vías de OSM comparten numeración; misma convención que `osm2pgsql` |
| Pesos iniciales | La migración 0005 inserta 0,50 / 0,30 / 0,20 como versión vigente del sistema (`id_usuario` NULL) si la tabla está vacía | Dato de referencia del modelo de la tesis, no un dato de prueba: sin pesos vigentes el motor no puede evaluar |
| `reporte.id_via` y `puntaje_prioridad` | Los escribe el motor en cada evaluación junto con la fila de `evaluacion_prioridad` | `id_via` NULL = "Revisar vía"; el puntaje es la copia de la U vigente para el ranking |
| Reporte activo | Todo estado salvo `reparado` | Al guardar pesos nuevos se recalculan los activos; un reporte reparado conserva su última evaluación |
| `servicio_critico.tipo` | `amenity=hospital` → hospital, `amenity=school` → escuela; ubicación del área = centro calculado por Overpass | Tipos del diagrama ER |

## Índices

- GiST sobre `reporte.ubicacion`, `servicio_critico.ubicacion`, `via.geom` y `zona.geom`.
- GiST de expresión sobre `::geography` en `reporte.ubicacion`, `servicio_critico.ubicacion` y `via.geom` (ADR 0003).
- Ranking: `reporte (estado, puntaje_prioridad DESC)`; además `fecha_creacion` e `id_usuario`.
- Historial y evaluaciones: `(id_reporte, fecha)`.
