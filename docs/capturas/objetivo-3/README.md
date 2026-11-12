# Capturas del panel administrativo (objetivo 3)

Capturas del panel tomadas el 2026-11-11 con la versión `v0.6.0`, en el equipo del responsable
(stack de Docker Compose, panel en `http://localhost:8080`), con Chromium a 1440 × 1000 y doble
resolución.

**Son una demostración de funcionamiento, no resultados de campo** (decisión 76 de la
[bitácora](../../bitacora.md)). Los datos vienen de `python -m app.cli seed-demo`: 32 reportes de
demostración sobre vías reales de Pasto, evaluados por el motor real, con fotos generadas que
llevan la franja «DEMO · imagen generada, no es una foto de campo».

| Archivo | Qué muestra | Historia |
|---|---|---|
| `01-inicio-de-sesion.png` | Ingreso de funcionarios | HU-10 |
| `02-priorizacion.png` | Indicadores por estado, mapa de calor y comienzo del ranking | HU-08 |
| `03-priorizacion-pagina-completa.png` | Lo mismo con las 20 filas del ranking y la paginación | HU-08 |
| `04-priorizacion-con-reportes-en-el-mapa.png` | Mapa con «Ver reportes»: marcadores agrupados | HU-08 |
| `05-priorizacion-filtro-priorizados.png` | Ranking filtrado por estado «priorizado» | HU-08 |
| `06-detalle-reporte-priorizado.png` | Evidencia, vía OSM, desglose de U e historial de estados | HU-12 |
| `07-detalle-reporte-sin-via.png` | Reporte sin vía a 30 m: F = 2 y marca «Revisar vía» | HU-12 |
| `08-pesos-del-modelo.png` | Pesos vigentes, reglas de normalización y versiones | HU-14 |
| `09-pesos-suma-invalida.png` | Aviso y guardado bloqueado cuando los pesos no suman 1,00 | HU-14 |

## Qué tener en cuenta al usarlas

- **El ranking mezcla 7 reportes de la prueba en el celular con los 32 de demostración.** Por eso
  los indicadores muestran 35 activos y en las capturas 02 a 05 aparecen filas con fecha «8 nov» y
  «21 oct». Los dos detalles (06 y 07) son de reportes de demostración.
- Los reportes de demostración tienen todos la fecha del día en que se cargaron («11 nov»).
- Los pesos son los iniciales (0,5 / 0,3 / 0,2): preliminares hasta la validación con el panel de
  expertos.
- La captura 03 se tomó con una ventana tan alta como la página, para que quepa el ranking entero.

## Cómo repetirlas

Con el stack levantado (README de la raíz, sección «Panel administrativo»): crear un administrador
con `create-admin`, cargar `seed-demo` y recorrer las pantallas. Las pruebas de punta a punta
(`infra/scripts/e2e-panel.sh`) recorren los mismos flujos en un stack aparte.
