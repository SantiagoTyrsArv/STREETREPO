import { divIcon } from "leaflet";
import { Marker, Tooltip } from "react-leaflet";
import { BaseMap } from "../../map/BaseMap";
import type { BlindCard } from "./api";
import { serviceLabel } from "./labels";

/** Zoom en el que caben los servicios a 500 m del daño. */
const BLIND_ZOOM = 16;
const PIN_SIZE_PX = 22;
const SERVICE_SIZE_PX = 16;

const damageIcon = divIcon({ className: "location-pin", iconSize: [PIN_SIZE_PX, PIN_SIZE_PX] });
const serviceIcon = divIcon({
  className: "service-pin",
  iconSize: [SERVICE_SIZE_PX, SERVICE_SIZE_PX],
});

/** Minimapa de la vista a ciegas: el daño y los servicios críticos cercanos, sin distancias. */
export function BlindMap({ card }: { card: BlindCard }) {
  const { latitude, longitude } = card.location;
  return (
    <BaseMap
      center={[latitude, longitude]}
      zoom={BLIND_ZOOM}
      className="blind-map"
      label="Mapa del daño y los servicios cercanos"
    >
      <Marker position={[latitude, longitude]} icon={damageIcon} title="Ubicación del daño" />
      {card.nearby_services.map((service) => (
        <Marker
          key={`${service.location.latitude}:${service.location.longitude}`}
          position={[service.location.latitude, service.location.longitude]}
          icon={serviceIcon}
          title={serviceLabel(service)}
        >
          <Tooltip>{serviceLabel(service)}</Tooltip>
        </Marker>
      ))}
    </BaseMap>
  );
}
