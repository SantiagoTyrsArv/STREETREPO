# Capturas del panel: comparación con el panel de referencia (objetivo 4)

Capturas tomadas el 2026-11-23 con la versión de `main` posterior a `v0.7.0`, con Chromium a
1440 × 1000 y doble resolución, en el stack aparte de pruebas (`street-repo-e2e`, panel en
`http://localhost:8081`). Se generan con
`CAPTURAS=1 infra/scripts/e2e-panel.sh e2e/capturas-objetivo-4.spec.ts`.

**Son una demostración de funcionamiento, no resultados de la prueba piloto.** Los reportes vienen
de `seed-demo`; las zonas «E2E Oeste» y «E2E Este» son rectángulos de prueba que crea el script,
no las zonas del estudio; la evaluadora es una cuenta temporal `@example.com` y su orden se armó
solo para recorrer el flujo. Las cifras de `09-resultados.png` no deben citarse como resultados.

| Archivo | Qué muestra |
|---|---|
| `01-zonas-del-estudio.png` | Zonas con su concentración y mapa |
| `02-abrir-ronda.png` | Formulario para abrir una ronda |
| `03-ronda-abierta-avance.png` | Ronda abierta, sin evaluadores todavía |
| `04-evaluador-mis-evaluaciones.png` | Vista de la evaluadora: zonas pendientes |
| `05-vista-a-ciegas.png` | Orden a ciegas de una zona (sin puntaje ni confirmaciones) |
| `06-confirmar-envio.png` | Confirmación antes de enviar el orden |
| `07-evaluador-zonas-enviadas.png` | Todas las zonas enviadas |
| `08-avance-con-evaluador.png` | Avance de la ronda con el evaluador anónimo |
| `09-resultados.png` | Resultados: coincidencia ±1, Spearman, Kendall, prueba entre zonas y deduplicación |
