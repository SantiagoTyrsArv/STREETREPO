# Capturas de la app ciudadana

Capturas tomadas el 2026-11-23 en el emulador de Android 15 (Pixel 7, AVD `streetrepo_pixel7`),
con la app compilada en modo depuración contra el stack aparte `street-repo-e2e` (base con OSM y
`seed-demo`) por `adb reverse`. Se quitó la barra de estado del sistema.

- La cuenta «Ciudadana de prueba» (`@example.com`) se creó solo para estas capturas y se suprimió
  al final desde la propia app (`15-constancia-supresion.png`).
- La ubicación se fijó con un proveedor de GPS de prueba junto a reportes de demostración; los
  reportes confirmados son de demostración, no de campo.
- Los estados sin conexión se provocaron quitando el `adb reverse` hacia la API.

| Archivo | Qué muestra | Historia |
|---|---|---|
| `01-mis-reportes-vacio.png` | Mis reportes sin reportes (estado vacío) | Estados |
| `02-posible-duplicado.png` | Aviso de reporte activo a 6 m, radio de 25 m | HU-15 |
| `03-confirmacion-desde-duplicado.png` | Confirmación registrada desde el aviso | HU-16 |
| `04-mis-reportes-confirmado.png` | El reporte confirmado aparece en Mis reportes | HU-16 |
| `05-mapa-ficha-confirmar.png` | Ficha del reporte en el mapa con «Confirmar este daño» | HU-16 |
| `06-mapa-ficha-confirmado.png` | Ficha después de confirmar | HU-16 |
| `07-confirmar-lejos-del-dano.png` | Rechazo a más de 50 m del daño | Propuesta 112 |
| `08-mapa-sin-conexion.png` | Mapa sin conexión con «Reintentar» | Estados |
| `09-mis-reportes-sin-conexion.png` | Mis reportes sin conexión | Estados |
| `10-perfil.png` | Perfil y privacidad | HU-11 |
| `11-editar-datos.png` | Editar nombre o correo | HU-11 |
| `12-datos-actualizados.png` | Perfil con el nombre actualizado | HU-11 |
| `13-solicitar-supresion.png` | Qué se elimina y qué se conserva | HU-11 |
| `14-supresion-falta-contrasena.png` | Validación: falta la contraseña | HU-11 |
| `15-constancia-supresion.png` | Constancia de la supresión atendida | HU-11 |
