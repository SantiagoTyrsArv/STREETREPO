Medidas del sistema en un equipo local con datos de demostración; no son resultados de campo ni del capítulo 4.

# Informe de carga — fase 8

> 2026-11-24 · decisión 68 · metas de la guía 11 · bitácora, fila 146

## Qué se midió

La API de Street Repo atendiendo a la vez a ciudadanos (app) y funcionarios (panel), con
Locust, contra un stack de Docker Compose aparte en el mismo equipo. Los escenarios están en
`backend/loadtests/locustfile.py` y se explican en `backend/loadtests/README.md`.

| | |
|---|---|
| Equipo | AMD Ryzen 7 7435HS (8 núcleos, 16 hilos), 23,7 GB de RAM, Windows 11 Home 10.0.26300 |
| Docker | Docker Desktop 29.9.3; máquina virtual con 16 CPU y 11,5 GB de RAM |
| API | imagen del repositorio (`infra/docker/api.Dockerfile`), **un solo proceso** de uvicorn, `LOG_LEVEL=WARNING` |
| Base | PostGIS 17-3.5 con las vías y servicios críticos de OSM de Pasto y los 32 reportes de `seed-demo` |
| Carga | 50 usuarios simultáneos (45 ciudadanos y 5 funcionarios), 5 nuevos por segundo, 5 minutos |
| Cupos | subidos solo en este stack para que una sola IP no se cortara (límite global, login, reportes y mapa); los valores por defecto no cambian |
| Cliente | Locust 2.47.0 en el mismo equipo, contra `http://localhost:8002` (sin red de por medio) |
| Comando | `infra/scripts/load-test.sh` |

Cada ciudadano, tras iniciar sesión, consulta el mapa por área visible, revisa los reportes
cercanos y a veces envía un reporte con una foto de 1600 × 1200 (~0,7 MB), que se recodifica, se
guarda y se evalúa (cálculo de U) en la misma transacción. Cada funcionario consulta el ranking y
el mapa de calor. Se esperan entre 1 y 5 segundos entre acciones.

## Resultados

6976 solicitudes en 5 minutos (23,3 por segundo de media; entre 9,6 y 24,9 por segundo con los
50 usuarios activos) y **1 fallo (0,01 %)**. Tiempos en milisegundos:

| Endpoint | Solicitudes | Fallos | Mediana | p95 | p99 | Máximo |
|---|---|---|---|---|---|---|
| `GET /reports?bbox` (mapa de la app) | 3556 | 0 | 12 | 27 | 54 | 120 |
| `GET /reports/nearby` (posible duplicado) | 2193 | 0 | 8 | 23 | 48 | 183 |
| `POST /reports` (foto, ubicación, severidad y U) | 755 | 0 | 86 | 140 | 200 | 254 |
| `GET /admin/ranking` | 278 | 1 | 12 | 34 | 91 | 2038 |
| `GET /admin/heatmap` | 144 | 0 | 11 | 28 | 71 | 107 |
| `POST /auth/login` | 50 | 0 | 2200 | 2300 | 2300 | 2349 |

## Comparación con las metas de la guía 11

| Meta | Medido | ¿Cumple? |
|---|---|---|
| Listados < 500 ms | p95 entre 23 y 34 ms; p99 entre 48 y 91 ms | **Sí**, con amplio margen |
| Envío de reporte < 3 s (con red 4G) | p95 de 140 ms en el servidor; máximo 254 ms | **Sí en el servidor**. La meta incluye la subida por 4G, que esta prueba no mide (cliente y servidor en el mismo equipo): con ~0,7 MB por foto, la red 4G pesa más que el servidor |

## Observaciones

- **El único fallo** fue una conexión cerrada sin respuesta en `GET /admin/ranking`
  (`RemoteDisconnected`), con 2038 ms. Ocurrió una vez entre 6976 solicitudes; la causa probable,
  no comprobada, es la carrera habitual entre el cierre de una conexión inactiva por uvicorn y su
  reutilización por el cliente. No hubo errores 5xx.
- **El inicio de sesión tarda unos 2,2 s** con 50 usuarios entrando en 10 segundos. Es lo esperado:
  Argon2id es lento a propósito (guía 7.1) y la API corre en un solo proceso. Ocurre una vez por
  sesión y no entra en las metas de la guía.
- **Limpieza:** al terminar se borraron las 60 cuentas de carga con sus 755 reportes y fotos, y los
  32 reportes de demostración; la base de carga quedó con 0 usuarios y 0 reportes.

## Limitaciones

- Un solo equipo, sin red real entre cliente y servidor: mide el servidor, no la experiencia en un
  celular con 4G.
- Datos de demostración (32 reportes al empezar, unos 790 al final), no el volumen de una ciudad.
- Una sola corrida. Para el capítulo 4 haría falta repetirla en el servidor de la prueba piloto.
- Cupos de solicitudes subidos en este stack; en uso normal, el límite global (600 cada 5 min por
  IP) y los de cada ruta siguen vigentes.

## Cómo repetirla

```bash
infra/scripts/load-test.sh                                  # la corrida de este informe
LOAD_DURATION=30s LOAD_USERS=5 infra/scripts/load-test.sh   # prueba de humo
```

Los CSV y el HTML de Locust quedan en `.superpowers/carga/<fecha-hora>/`, fuera de git (desde la
fila 149; la corrida de este informe se guardó antes en `.superpowers/carga/` y una corrida
posterior la sobrescribió: sus cifras salen de la salida de consola, publicada en Linear, ARE-48).
