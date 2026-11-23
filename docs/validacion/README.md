# Zonas del estudio de validación (objetivo 4)

Las zonas se cargan con:

```bash
POSTGRES_HOST=127.0.0.1 POSTGRES_PORT=5433 uv run python -m app.cli zones-import ruta/zonas.geojson
```

Responde `Zonas cargadas: N · reportes asignados: M`. Si el archivo no cumple las reglas, no guarda
nada y explica el problema en español.

## Formato

Un GeoJSON `FeatureCollection` (coordenadas WGS 84, longitud y luego latitud) con:

- de 1 a 3 zonas (`MAX_ZONES`), cada una un `Polygon` (no `MultiPolygon`);
- `properties.name`: nombre único de la zona;
- `properties.concentration`: `alta` o `baja` (concentración de reportes de la zona);
- polígonos válidos que no se solapen entre sí ni con las zonas ya cargadas.

Para abrir una ronda, cada zona necesita al menos 5 reportes activos con U (`MIN_REPORTS_PER_ZONE`).

Volver a cargar el archivo actualiza las zonas por nombre y reasigna la zona de todos los reportes.
Las zonas cargadas antes que no vengan en el archivo nuevo no se tocan.

## Ejemplo

> **Ejemplo ficticio**: estas coordenadas son cuadrados de ilustración, no las zonas del estudio.
> Las zonas reales se dibujan sobre el mapa de Pasto con el responsable.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": { "name": "Zona de ejemplo A", "concentration": "alta" },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-77.285, 1.210], [-77.275, 1.210], [-77.275, 1.218], [-77.285, 1.218], [-77.285, 1.210]]]
      }
    },
    {
      "type": "Feature",
      "properties": { "name": "Zona de ejemplo B", "concentration": "baja" },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-77.300, 1.195], [-77.290, 1.195], [-77.290, 1.203], [-77.300, 1.203], [-77.300, 1.195]]]
      }
    }
  ]
}
```

El anillo de cada polígono cierra en el mismo punto en que empieza.

Decisiones del estudio en [ADR 0008](../adr/0008-validacion-panel-referencia.md).
