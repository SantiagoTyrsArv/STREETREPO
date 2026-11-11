import { divIcon } from "leaflet";
import { Marker } from "react-leaflet";
import { BaseMap } from "../../map/BaseMap";

/** Zoom de calle, suficiente para reconocer la cuadra del daño. */
const DETAIL_ZOOM = 17;
const PIN_SIZE_PX = 22;

const pinIcon = divIcon({
  className: "location-pin",
  iconSize: [PIN_SIZE_PX, PIN_SIZE_PX],
});

/** Punto exacto del reporte; solo lo ve el panel administrativo (guía 7.2). */
export function LocationMap({ lat, lon }: { lat: number; lon: number }) {
  return (
    <BaseMap
      center={[lat, lon]}
      zoom={DETAIL_ZOOM}
      className="location-map"
      label="Ubicación del reporte"
    >
      <Marker position={[lat, lon]} icon={pinIcon} title="Ubicación del daño" />
    </BaseMap>
  );
}
