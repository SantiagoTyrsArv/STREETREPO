# Fotos de demostración

Imágenes que usa `python -m app.cli seed-demo` como evidencia de los reportes de demostración
del panel (decisión 76 de `docs/bitacora.md`). **No son fotos de campo.**

- **Origen:** imágenes sintéticas dibujadas con Pillow por `infra/scripts/generate_demo_photos.py`
  (pavimento, huecos y grietas simulados). No se tomaron con una cámara ni salen de un banco de
  imágenes.
- **Licencia:** obra propia del proyecto, sin derechos de terceros.
- **Metadatos:** no tienen EXIF; además, `seed-demo` las recodifica con el mismo procesador de
  fotos de los reportes reales.
- **Marca:** cada imagen lleva una franja que dice «DEMO · imagen generada, no es una foto de
  campo», para que una captura del panel no se confunda con evidencia real.

Para regenerarlas (el resultado es siempre el mismo):

```bash
cd backend && uv run python ../infra/scripts/generate_demo_photos.py
```

Se pueden reemplazar por fotos propias del responsable (archivos `.jpg`, sin personas, placas ni
fachadas reconocibles); en ese caso hay que actualizar este archivo con su origen y licencia.
