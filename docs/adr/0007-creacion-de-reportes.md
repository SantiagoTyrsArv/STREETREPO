# 0007 · Creación de reportes: foto, área de servicio, límites e idempotencia

- **Fecha:** 2026-10-19
- **Estado:** Aceptada
- **Refs:** HU-02, HU-05, HU-07, HU-15, propuestas 11, 34, 35, 36, 37, 38 y 41

## Ruta

`POST /api/v1/reports`, solo con sesión, en `multipart/form-data`:

| Campo | Regla |
|---|---|
| `photo` | Obligatoria; JPEG, PNG o WebP según su contenido; hasta 10 MB |
| `longitude`, `latitude` | Obligatorias, en grados decimales WGS 84, dentro de `REPORT_AREA_BBOX` |
| `severity` | `baja`, `media` o `alta` (en la base, el código ordinal 1, 2 o 3) |
| `description` | Opcional, hasta 500 caracteres; en blanco se guarda como NULL |
| `create_anyway` | Opcional, `false` por defecto; `true` crea el reporte aunque haya otro activo a 25 m |
| Cabecera `Idempotency-Key` | Opcional, UUID |

Responde **201** con el reporte ya evaluado: estado, U, dirección y la marca «Revisar vía». El autor ve
la ubicación exacta (propuesta 40).

## Decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Una sola transacción | Reporte, historial (`registrado` por el ciudadano y `evaluado` por el sistema), evidencia y evaluación del motor se confirman juntos | Guía 4.4 (Unit of Work) y 4.5: si el motor falla, no queda un reporte sin evaluar |
| Archivos de la foto | Se escriben antes de la transacción y se borran si no se confirma; si el borrado falla, se registra, no oculta el error original y el archivo lo recoge después `purge-orphan-photos` (ADR 0006) | Un archivo huérfano no se sirve a nadie porque no tiene fila en `evidencia`; un reporte sin su foto sí sería un dato incoherente |
| Almacenamiento (propuesta 34) | Disco, detrás del puerto `PhotoStorage`; en Docker, el volumen `photos`, que entra en los respaldos junto con la base (README). `evidencia.url_foto` guarda la clave relativa `ab/<uuid>.jpg`; la miniatura es `ab/<uuid>_min.jpg` | La clave aleatoria no revela el reporte, el usuario ni el nombre del archivo original. Las escrituras son atómicas y la ruta se verifica para que no salga de la carpeta |
| Procesado (propuesta 35) | Pillow: formato según el contenido decodificado; tope de 50 MP antes de decodificar; se aplica la orientación EXIF; se compone sobre blanco si hay transparencia; se recodifica **siempre** a JPEG calidad 85 con lado máximo de 1600 px y miniatura de 400 px, sin `exif` ni `icc_profile` | Guía 7.2: no se guarda el archivo del cliente, así que no quedan GPS, marca ni modelo del dispositivo |
| Errores de la foto | **413** `PHOTO_TOO_LARGE`, **415** `PHOTO_UNSUPPORTED_TYPE`, **422** `PHOTO_INVALID` (dañada o demasiados píxeles) | Guía 6.1 |
| Área de servicio (propuesta 37) | `REPORT_AREA_BBOX`, por defecto igual a `OSM_BBOX` (que ya deja margen alrededor del casco urbano); se valida al arrancar. Fuera de ella: **422** `LOCATION_OUTSIDE_SERVICE_AREA`, antes de consumir cupo | Fuera de los datos OSM cargados, F y P no tendrían sentido |
| Límites (propuesta 38) | 10 reportes por hora por usuario (`REPORT_RATE_LIMITED`) y 30 por hora por IP (`RATE_LIMITED`), configurables con `REPORTS_PER_USER_PER_HOUR` y `REPORTS_PER_IP_PER_HOUR`; **429** con `Retry-After` | Mismo limitador en memoria de la decisión 25, con su misma limitación (un proceso; se reinicia con la API) |
| Idempotencia (propuesta 11) | Si el usuario ya creó un reporte con la clave, se responde **200** con ese reporte, sin procesar la foto ni consumir cupo. Si dos envíos con la misma clave llegan a la vez, la restricción única decide y el segundo recibe el reporte del primero | Reintentos de la app en red móvil inestable (guía 10.3). No se compara el contenido del reintento con el original: la clave identifica el envío |
| Dirección (propuesta 41) | `address` es el nombre de la vía OSM asociada; si la vía no tiene nombre, «Vía sin nombre»; si no hay vía a 30 m, «Sin vía asociada». `reporte.direccion` queda en NULL | Sin Nominatim en la ruta del usuario (guía 3.1) |
| Dependencias nuevas | `pillow` (procesado) y `python-multipart` (FastAPI lo necesita para leer formularios con archivos) | Decisión menor (guía 3) |

## Posible duplicado a 25 m (propuesta 36, HU-15)

- `GET /api/v1/reports/nearby?longitude=…&latitude=…` (con sesión) lista hasta 10 reportes activos
  (todo estado salvo reparado, decisión 13) a 25 m, del más cercano al más lejano: `id`,
  `location` (pública), `distance_m` (un decimal), `status`, `severity`, `confirmations`,
  `address` y `created_at`. No incluye autor, descripción ni ubicación exacta (guía 7.2).
- El punto consultado debe estar dentro de `REPORT_AREA_BBOX` (**422**
  `LOCATION_OUTSIDE_SERVICE_AREA`) y cada usuario tiene un cupo propio de consultas por hora,
  con el valor de `REPORTS_PER_USER_PER_HOUR` (**429** `NEARBY_RATE_LIMITED`).
- `POST /api/v1/reports` repite la búsqueda en el servidor y responde **409**
  `REPORT_DUPLICATE_NEARBY` con la misma lista en `details.items`, salvo que llegue
  `create_anyway=true`. Así decide el ciudadano (guía 2.5), pero un cliente que se salte la pantalla
  no crea duplicados sin querer.

| Tema | Decisión | Motivo |
|---|---|---|
| Orden de las verificaciones | Primero la clave de idempotencia; después el área, el tamaño, los duplicados, el cupo y la foto | Un reintento encontraría su propio reporte a 0 m: debe devolverse con 200, no como duplicado (condición del responsable). Un 409 no consume cupo ni procesa la foto |
| Misma transacción (condición del responsable) | Justo antes de insertar se toma un candado de transacción de PostgreSQL (`pg_advisory_xact_lock`) y se repiten la búsqueda por clave de idempotencia y la de duplicados; el candado se libera al confirmar o revertir | Sin candado, dos ciudadanos que reportan el mismo hueco a la vez pasarían ambos la verificación. Con él, el segundo ve el reporte del primero (409) o, si es un reintento con la misma clave, recibe el reporte ya creado (200) |
| Alcance del candado | Uno solo para toda la creación de reportes, no por zona | Dura milisegundos (la foto ya está procesada y guardada) y a la escala del MVP es más simple y seguro que bloquear por celdas, que fallan en los bordes |
| Ubicación pública (propuestas 40 y 43) | `location` es la ubicación exacta ajustada a una cuadrícula de 0,0001° (`ST_SnapToGrid`, unos 11 m) y `distance_m` se mide desde ella, en `nearby` y en el 409 | Con la distancia exacta y tres consultas desde puntos distintos se calculaba la ubicación real (trilateración). Medida desde la pública, la trilateración solo recupera lo que ya se muestra |
| Cupo de `nearby` | Cuenta propia (`nearby:user:<id>`), con el mismo valor que el de crear reportes | Consultar antes de enviar no debe gastar el cupo del envío |
| Riesgo residual | Quién entra en la lista se decide con la ubicación **exacta** a 25 m (la deduplicación lo exige). Sondeando muchos puntos en el borde del círculo se podría acercar a la ubicación real | Lo acotan el cupo por usuario, el área de servicio y la sesión obligatoria: con 10 consultas por hora, el sondeo toma días por reporte. Si hiciera falta más, usar la ubicación pública también para decidir la lista de `nearby` (no la del 409) |
| Duplicado detectado ya con el candado | 409, se revierte la transacción y se borran los archivos; el cupo de esa solicitud ya se consumió | Solo pasa si otro reporte cercano se creó en el mismo instante |

## Servir la foto (propuesta 34)

`GET /api/v1/reports/{id}/photo` (hasta 1600 px) y `GET /api/v1/reports/{id}/photo/thumbnail`
(hasta 400 px), con sesión, responden `image/jpeg`.

| Tema | Decisión | Motivo |
|---|---|---|
| Quién la ve | El autor del reporte y los administradores (`can_view_photo`) | Puede mostrar rostros, placas o fachadas (guía 7.2) |
| Respuesta cuando no puede verla | **404** `PHOTO_NOT_FOUND`, igual si el reporte no existe, no tiene foto o es de otro ciudadano | No revela si existe un reporte ajeno (IDOR, guía 7.1) |
| Caché | `Cache-Control: private, no-store` | Tras una supresión no deben quedar copias en el navegador ni en intermediarios (Ley 1581). El costo es volver a descargarla; las fotos pesan pocos cientos de KB |
| Archivo que falta | Si la fila de `evidencia` existe pero el archivo no, se registra un error y se responde 404 | Es una inconsistencia que hay que revisar, no un error del cliente |
| Varias fotos | Se sirve la más reciente del reporte | Hoy cada reporte tiene una sola; la ruta no cambia si llegan más |

## Pendiente

- **Tamaño del cuerpo:** la API rechaza la foto de más de 10 MB después de recibirla. Con el proxy HTTPS (HU-17), limitar ahí el tamaño de la petición para no recibir cuerpos enormes.
