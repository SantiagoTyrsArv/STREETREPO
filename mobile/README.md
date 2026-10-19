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

En el emulador de Android el computador es `10.0.2.2`. La prueba en un celular real se documenta
al cerrar la app (tarea 7 del plan).
