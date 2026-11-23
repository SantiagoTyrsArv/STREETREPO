import type { GeoJsonObject } from "geojson";
import { GeoJSON, Tooltip } from "react-leaflet";
import type { Zone } from "./api";
import { concentrationLabel } from "./labels";

/** Polígonos de las zonas; el color sale de los tokens por clase (`validation.css`). */
export function ZonePolygons({ zones }: { zones: readonly Zone[] }) {
  return zones.map((zone) => (
    <GeoJSON
      // Leaflet no actualiza la geometría de una capa ya creada: la clave la renueva.
      key={`${zone.id}:${JSON.stringify(zone.geometry)}`}
      data={zone.geometry as unknown as GeoJsonObject}
      style={{ className: `zone-shape zone-shape--${zone.concentration}` }}
    >
      <Tooltip sticky>
        {zone.name} · {concentrationLabel(zone.concentration)}
      </Tooltip>
    </GeoJSON>
  ));
}
