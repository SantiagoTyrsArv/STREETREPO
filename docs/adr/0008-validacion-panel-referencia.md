# 0008 · Validación con el panel de referencia: zonas, rondas, vista a ciegas, métricas y avisos

- **Fecha:** 2026-11-23
- **Estado:** Aceptada
- **Refs:** HU-09, HU-15, HU-16, propuesta 114, decisión 115 (diseño en
  `docs/superpowers/specs/2026-11-22-objetivo-4-comparacion-panel-referencia-design.md`)

Backend del objetivo 4 de la tesis: comparar el ranking del motor con el orden que da un panel
de expertos («evaluadores») y medir la deduplicación por zona. El panel web llega en la entrega 2.

## Flujo

1. El administrador carga las zonas con `python -m app.cli zones-import zonas.geojson`
   ([formato](../validacion/README.md)). Cada reporte guarda la zona que lo cubre (`reporte.id_zona`).
2. Crea las cuentas de los evaluadores con `python -m app.cli create-evaluator`.
3. Abre una ronda (`POST /admin/evaluation-rounds`): se congela una muestra de reportes activos
   de cada zona con su U y el orden del motor.
4. Cada evaluador ve la ronda a ciegas (`/evaluation/current/...`) y envía un orden por zona.
5. El administrador cierra la ronda y descarga los resultados y la ficha comparativa.

## Decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Zonas | GeoJSON `FeatureCollection` de `Polygon` con `name` y `concentration` (`alta`/`baja`); máximo `MAX_ZONES` = 3; sin solapes ni geometrías inválidas (lo verifica PostGIS); se actualizan por nombre y se reasignan todos los reportes con `ST_Covers` | El estudio compara zonas de alta y baja concentración; una zona por reporte evita contarlo dos veces |
| Rol evaluador | Nuevo valor `evaluador` de `rol_usuario`. Entra al panel por la misma sesión web que el administrador (`STAFF_ROLE_REQUIRED` si es ciudadano); no crea reportes ni confirma (`EVALUATOR_CANNOT_REPORT`) ni entra a `/admin` | Separa al panel de expertos de los datos del motor y de la operación |
| Muestra congelada | Al abrir, por zona: reportes activos con U y zona, `MIN_REPORTS_PER_ZONE` = 5 como mínimo; si sobran, muestreo con semilla (`Random(semilla + id_zona)`) y orden del motor con el mismo desempate del ranking (guía 2.2) más el id. Se guardan U y `orden_motor` en `ronda_reporte` y la versión de pesos en la ronda. Una sola ronda abierta (índice único parcial) | La comparación debe ser reproducible aunque cambien los pesos o los reportes después |
| Vista a ciegas | El evaluador ve por tarjeta solo descripción, vía, severidad, ubicación y servicios críticos a 500 m (sin distancia); la zona sin su concentración; las tarjetas barajadas por evaluador. Ninguna respuesta lleva U, factores, estado, fechas, confirmaciones ni datos de otros evaluadores | Evitar el sesgo de anclaje: el panel debe ordenar con la información de campo, no con la del motor |
| Envío del orden | Un orden estricto 1..n por zona, una sola vez (`409` si repite); se guarda en una transacción con la ronda bloqueada `FOR SHARE` para que no se cierre a medias. Si llega un segundo envío inválido, responde primero el 409 | Un orden parcial o cambiado después invalidaría la comparación |
| Métricas (propuesta 114) | Por zona: orden del panel = rangos promedio de la posición media; rho de Spearman y tau-b de Kendall (también por evaluador); W de Kendall con 2 o más evaluadores; coincidencia ±1. Entre zonas: desacuerdo \|motor − panel\| / (n − 1) y Mann-Whitney (dos zonas) o Kruskal-Wallis (tres), α = 0,05. Funciones puras con `scipy` | Las correlaciones de rangos miden el acuerdo con su significancia; el porcentaje de coincidencia solo describe |
| Resultados | `GET /admin/evaluation-rounds/{id}/results` solo con la ronda cerrada (`409 EVALUATION_ROUND_STILL_OPEN`). Una zona sin órdenes queda sin métricas y fuera de la prueba entre zonas | Con la ronda abierta las cifras aún pueden cambiar |
| Ficha en CSV | `ficha.csv` (una fila por reporte, `orden_evaluador_k`) y `resumen.csv` (una fila por zona y una `entre_zonas`) con la ronda cerrada; `reportes.csv` y `avisos.csv` siempre, para la revisión manual de duplicados. UTF-8 con BOM, punto decimal, `Cache-Control: private, no-store` | Punto para el análisis; BOM para que la hoja de cálculo lea las tildes |
| Anonimato del panel | Los evaluadores solo aparecen como «Evaluador k», numerados por su primer envío en la ronda (desempate por id); ningún archivo ni respuesta lleva su nombre, correo o id | Ley 1581, minimización |
| Avisos de duplicado | Cada vez que el servidor ofrece candidatos a 25 m (`GET /reports/nearby` con resultados o el 409 de `POST /reports`) se guarda un aviso «pendiente» con la zona del punto (no el punto) y los candidatos con su distancia exacta al reporte. La app devuelve `duplicate_warning_id` al confirmar («confirmo») o al crear con `create_anyway` («creo_igual»), en la misma transacción. Un id ajeno, ya resuelto o, para «confirmo», de un reporte que no era candidato no cambia el aviso ni impide la acción | Medir cuántos duplicados se evitaron sin guardar la ubicación de quien consulta |
| Carrera del 409 | La segunda verificación de duplicados (con el candado de creación) no registra aviso | Es un caso raro y registrarlo obligaría a confirmar la transacción a medias |
| Deduplicación por zona | Cuenta todos los reportes y avisos de cada zona de la ronda, no solo la muestra; los avisos fuera de toda zona no entran | El objetivo mide la deduplicación de la zona, no la de la muestra |
| Borrado | La ronda borra en cascada sus reportes congelados y órdenes; un reporte en una ronda no se borra (`RESTRICT`); `aviso_duplicado.id_usuario` es `RESTRICT` porque las cuentas se anonimizan, no se borran (decisión 23a) | Conservar la evidencia del estudio |

## Límites conocidos

- Los avisos existen desde la migración 0009: lo anterior no se puede medir (se dice así en la tesis).
- Falsear la ubicación sigue siendo posible: los avisos registran lo que el servidor ofreció.
- `nearby_services` de la vista a ciegas no tiene tope; con los datos de Pasto son pocos por reporte.
