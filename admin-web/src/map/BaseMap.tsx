import "leaflet/dist/leaflet.css";
import type { ReactNode } from "react";
import { MapContainer, TileLayer } from "react-leaflet";
import { config } from "../config";
import "./map.css";

/** Centro del área de servicio de Pasto (`REPORT_AREA_BBOX` de la API): latitud, longitud. */
export const PASTO_CENTER: [number, number] = [1.205, -77.28];
export const DEFAULT_ZOOM = 14;

/** Atribución obligatoria de OpenStreetMap (guía 3.1). El enlace lo arma Leaflet, no React. */
const OSM_ATTRIBUTION =
  '&copy; colaboradores de <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

/**
 * La política de uso de las teselas de OSM exige un `Referer` válido; sin él responde una imagen
 * de «Access blocked». El panel se sirve con `Referrer-Policy: no-referrer`, así que solo las
 * teselas envían el origen (nunca la ruta, que lleva el identificador del reporte).
 */
const TILE_REFERRER_POLICY = "strict-origin";

type Props = {
  center?: [number, number];
  zoom?: number;
  className?: string;
  /** Nombre del mapa para lectores de pantalla. */
  label: string;
  children?: ReactNode;
};

/** Mapa base del panel: teselas configurables (`VITE_TILE_URL`) y atribución de OSM. */
export function BaseMap({
  center = PASTO_CENTER,
  zoom = DEFAULT_ZOOM,
  className,
  label,
  children,
}: Props) {
  return (
    <div className={className} role="region" aria-label={label}>
      <MapContainer center={center} zoom={zoom} className="base-map" scrollWheelZoom>
        <TileLayer
          url={config.tileUrl}
          attribution={OSM_ATTRIBUTION}
          referrerPolicy={TILE_REFERRER_POLICY}
        />
        {children}
      </MapContainer>
    </div>
  );
}
