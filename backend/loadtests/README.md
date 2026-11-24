# Pruebas de carga (Locust)

Fase 8, decisión 68. Miden la API contra las metas de la guía 11 (listados < 500 ms; envío
de reporte < 3 s). **Las cifras son medidas del sistema en un equipo local con datos de
demostración, no resultados de campo ni del capítulo 4.** El último informe está en
[`docs/rendimiento/informe-carga-fase-8.md`](../../docs/rendimiento/informe-carga-fase-8.md).

## Cómo correrla

Desde la raíz del repositorio, con Docker en marcha y el `.env` completo (Git Bash en Windows):

```bash
infra/scripts/load-test.sh                         # 50 usuarios, 5 por segundo, 5 minutos
LOAD_DURATION=30s LOAD_USERS=5 infra/scripts/load-test.sh   # prueba de humo
```

El script:

1. levanta un stack aparte (`street-repo-load`: base `streetrepo_load`, API en el puerto 8002),
   con los límites de solicitudes subidos **solo ahí**;
2. carga OSM la primera vez, `seed-demo`, 60 cuentas de ciudadano
   (`loadtest-accounts --count 60`, en `@carga.example.com`) y un administrador, todas con
   contraseñas aleatorias que no se guardan;
3. corre `locustfile.py` sin interfaz y deja los CSV y el HTML en
   `.superpowers/carga/<fecha-hora>/` (fuera de git), una carpeta por corrida;
4. al terminar, aunque falle, borra las cuentas de carga (con sus reportes y fotos) y los datos
   de demostración, y detiene el stack.

Variables: `LOAD_USERS`, `LOAD_SPAWN_RATE`, `LOAD_DURATION`, `LOAD_ACCOUNTS`,
`LOAD_DB_PORT` y `LOAD_API_PORT`. Los argumentos extra van a Locust.

## Escenarios

| Usuario | Peso | Tareas (peso) | Espera |
|---|---|---|---|
| Ciudadano (app) | 9 | mapa por área visible `GET /reports?bbox` (5), `GET /reports/nearby` (3), `POST /reports` con una foto de 1600 × 1200 (~0,7 MB) y `create_anyway=true` (1) | 1 a 3 s |
| Funcionario (panel) | 1 | `GET /admin/ranking` (2), `GET /admin/heatmap` (1) | 2 a 5 s |

Cada usuario inicia sesión una vez al empezar (`POST /auth/login`, Argon2id: lento a propósito).
`POST /reports` incluye el procesamiento de la foto y el cálculo de U en la misma transacción.
