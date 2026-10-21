# App ciudadana

App Flutter de Street Repo para Android: registro con la política de datos, reporte de daños con
foto, GPS y severidad, aviso de posible duplicado y seguimiento de los reportes propios y
confirmados. Diseño en `docs/superpowers/specs/2026-10-19-app-flutter-flujo-critico-design.md`.

## Requisitos

- Flutter 3.47 (canal stable) con el SDK de Android (plataforma 36, NDK 28.2) y JDK 17.
- Backend corriendo (ver el README de la raíz).

## Estructura

```
lib/
├─ app.dart, main.dart
├─ core/        # configuración, tema (tokens de la guía 10.1), formatos, red, rutas, componentes
└─ features/    # auth, report_new, my_reports, profile; cada una con
                # presentation / application / domain / data
assets/
├─ fonts/       # Archivo y Manrope (licencia OFL)
└─ icons/       # iconos SVG exportados del Figma
```

Estado con Riverpod (decisión 1), rutas con `go_router`, HTTP con `dio`. La app no calcula nada
del dominio: muestra lo que responde la API.

## Pruebas y calidad

```bash
cd mobile
flutter pub get
dart format --output=none --set-exit-if-changed .
flutter analyze
flutter test
```

## Ejecutar

La URL del backend se pasa al compilar; no hay valor por defecto:

```bash
flutter run --dart-define=API_BASE_URL=http://<ip-del-computador>:8000
```

En el emulador de Android el computador es `10.0.2.2`. La variante *debug* acepta HTTP sin cifrar
(`android/app/src/debug/res/xml/network_security_config.xml`); la de *release* exige HTTPS (HU-17).

### En un celular Android por cable USB (recomendado)

`adb reverse` reenvía un puerto del celular al computador por el cable: la API sigue publicada solo
en `127.0.0.1`, sin abrir el firewall ni depender de la red Wi-Fi.

1. Levantar el backend (en la raíz del repositorio):
   `docker compose -f infra/docker-compose.yml --env-file .env up -d --build`. Si la base no tiene
   datos OSM, cargarlos una vez:
   `docker compose -f infra/docker-compose.yml --env-file .env run --rm api python -m app.cli osm-import`.
2. Activar la depuración USB en el celular, conectarlo y comprobar que `adb devices` lo lista como
   `device` (aceptar en el celular la huella del computador).
3. Reenviar el puerto (repetirlo cada vez que se reconecte el cable):
   `adb reverse tcp:8000 tcp:<API_PORT>` (con el valor por defecto, `tcp:8000 tcp:8000`).
4. `flutter run --debug --dart-define=API_BASE_URL=http://127.0.0.1:8000`

### Alternativa: por la red Wi-Fi

Sin cable, el celular llega a la API por la IP local del computador:

1. Poner en `.env` `API_BIND_ADDRESS=<ip-wifi-del-computador>` (`ipconfig`) y levantar el backend.
2. Marcar la red Wi-Fi como **Privada** y permitir el puerto solo en ese perfil (PowerShell como
   administrador):
   ```powershell
   New-NetFirewallRule -DisplayName "Street Repo API (dev)" -Direction Inbound -Protocol TCP -LocalPort 8000 -Profile Private -Action Allow
   ```
3. `flutter run --debug --dart-define=API_BASE_URL=http://<ip-wifi-del-computador>:8000`

Al terminar, volver a `API_BIND_ADDRESS=127.0.0.1` para no dejar la API expuesta.

### Lista de verificación manual

Recorrido del flujo crítico en el celular, con la ubicación real en Pasto. Marcado con el resultado
de la prueba del 2026-10-21 (decisión 65 de la bitácora):

- [x] Crear cuenta aceptando la política de datos e ingresar.
- [x] Conceder cámara y ubicación desde la pantalla de permisos.
- [x] Tomar la foto y obtener la ubicación (precisión ≤ 30 m).
- [x] Elegir la severidad y enviar; ver «Reporte enviado».
- [x] El reporte aparece en Mis reportes como «Evaluado», con la dirección de la vía.
- [x] Reportar otra vez en el mismo lugar: «Posible duplicado» lo marca como «Tu reporte».
- [ ] Con una segunda cuenta, confirmar ese reporte; la segunda cuenta lo ve en Mis reportes con
  «Lo confirmaste». Para que aparezca el aviso, la ubicación debe quedar a menos de 25 m.
- [ ] Cortar la red durante un envío y luego «Reintentar»: se crea un solo reporte. Con el cable
  conectado el modo avión no corta la API; usar `adb reverse --remove tcp:8000` y volver a
  reenviar el puerto antes de «Reintentar».
- [x] Cerrar sesión: vuelve a la Bienvenida.
