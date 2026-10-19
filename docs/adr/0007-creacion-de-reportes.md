# 0007 · Creación de reportes: foto, área de servicio, límites e idempotencia

- **Fecha:** 2026-10-19
- **Estado:** Aceptada
- **Refs:** HU-02, HU-05, HU-07, propuestas 11, 34, 35, 37, 38 y 41

## Ruta

`POST /api/v1/reports`, solo con sesión, en `multipart/form-data`:

| Campo | Regla |
|---|---|
| `photo` | Obligatoria; JPEG, PNG o WebP según su contenido; hasta 10 MB |
| `longitude`, `latitude` | Obligatorias, en grados decimales WGS 84, dentro de `REPORT_AREA_BBOX` |
| `severity` | `baja`, `media` o `alta` (en la base, el código ordinal 1, 2 o 3) |
| `description` | Opcional, hasta 500 caracteres; en blanco se guarda como NULL |
| Cabecera `Idempotency-Key` | Opcional, UUID |

Responde **201** con el reporte ya evaluado: estado, U, dirección y la marca «Revisar vía». El autor ve
la ubicación exacta (propuesta 40).

## Decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Una sola transacción | Reporte, historial (`registrado` por el ciudadano y `evaluado` por el sistema), evidencia y evaluación del motor se confirman juntos | Guía 4.4 (Unit of Work) y 4.5: si el motor falla, no queda un reporte sin evaluar |
| Archivos de la foto | Se escriben antes de la transacción y se borran si no se confirma; si el borrado falla, se registra y no oculta el error original | Un archivo huérfano no se sirve a nadie porque no tiene fila en `evidencia`; un reporte sin su foto sí sería un dato incoherente |
| Almacenamiento (propuesta 34) | Disco, detrás del puerto `PhotoStorage`; en Docker, el volumen `photos`, que entra en los respaldos junto con la base (README). `evidencia.url_foto` guarda la clave relativa `ab/<uuid>.jpg`; la miniatura es `ab/<uuid>_min.jpg` | La clave aleatoria no revela el reporte, el usuario ni el nombre del archivo original. Las escrituras son atómicas y la ruta se verifica para que no salga de la carpeta |
| Procesado (propuesta 35) | Pillow: formato según el contenido decodificado; tope de 50 MP antes de decodificar; se aplica la orientación EXIF; se compone sobre blanco si hay transparencia; se recodifica **siempre** a JPEG calidad 85 con lado máximo de 1600 px y miniatura de 400 px, sin `exif` ni `icc_profile` | Guía 7.2: no se guarda el archivo del cliente, así que no quedan GPS, marca ni modelo del dispositivo |
| Errores de la foto | **413** `PHOTO_TOO_LARGE`, **415** `PHOTO_UNSUPPORTED_TYPE`, **422** `PHOTO_INVALID` (dañada o demasiados píxeles) | Guía 6.1 |
| Área de servicio (propuesta 37) | `REPORT_AREA_BBOX`, por defecto igual a `OSM_BBOX` (que ya deja margen alrededor del casco urbano); se valida al arrancar. Fuera de ella: **422** `LOCATION_OUTSIDE_SERVICE_AREA`, antes de consumir cupo | Fuera de los datos OSM cargados, F y P no tendrían sentido |
| Límites (propuesta 38) | 10 reportes por hora por usuario (`REPORT_RATE_LIMITED`) y 30 por hora por IP (`RATE_LIMITED`), configurables con `REPORTS_PER_USER_PER_HOUR` y `REPORTS_PER_IP_PER_HOUR`; **429** con `Retry-After` | Mismo limitador en memoria de la decisión 25, con su misma limitación (un proceso; se reinicia con la API) |
| Idempotencia (propuesta 11) | Si el usuario ya creó un reporte con la clave, se responde **200** con ese reporte, sin procesar la foto ni consumir cupo. Si dos envíos con la misma clave llegan a la vez, la restricción única decide y el segundo recibe el reporte del primero | Reintentos de la app en red móvil inestable (guía 10.3). No se compara el contenido del reintento con el original: la clave identifica el envío |
| Dirección (propuesta 41) | `address` es el nombre de la vía OSM asociada; si la vía no tiene nombre, «Vía sin nombre»; si no hay vía a 30 m, «Sin vía asociada». `reporte.direccion` queda en NULL | Sin Nominatim en la ruta del usuario (guía 3.1) |
| Dependencias nuevas | `pillow` (procesado) y `python-multipart` (FastAPI lo necesita para leer formularios con archivos) | Decisión menor (guía 3) |

## Pendiente

- **Posible duplicado a 25 m** (propuesta 36): `GET /api/v1/reports/nearby` y el 409 en esta ruta, en la rama siguiente.
- **Servir la foto** por una ruta que verifique el acceso (dueño y administradores, propuesta 34): con el detalle del reporte.
- **Fotos en la supresión** (propuesta 39): borrar fotos y miniaturas del titular.
- **Tamaño del cuerpo:** la API rechaza la foto de más de 10 MB después de recibirla. Con el proxy HTTPS (HU-17), limitar ahí el tamaño de la petición para no recibir cuerpos enormes.
