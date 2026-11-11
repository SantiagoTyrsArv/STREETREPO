// El orden importa: `leafletGlobal` publica `window.L` antes de cargar el complemento.
import { globalLeaflet } from "../../map/leafletGlobal";
import "leaflet.markercluster";
import "leaflet.markercluster/dist/MarkerCluster.css";
import { divIcon, marker, type Layer } from "leaflet";
import { HeatLayer } from "leaflet.heat";
import { useEffect } from "react";
import { useMap } from "react-leaflet";
import { formatScore } from "../../format/format";
import { BaseMap } from "../../map/BaseMap";
import type { HeatPoint } from "./api";

/** U va de 0 a 10; la capa de calor espera intensidades de 0 a 1. */
const U_MAX = 10;
const HEAT_RADIUS_PX = 28;
const HEAT_BLUR_PX = 20;
const HEAT_MIN_OPACITY = 0.35;
/**
 * Zoom desde el que cada punto pinta con toda su intensidad. Por defecto sería el zoom máximo
 * del mapa, y a escala de ciudad un reporte aislado casi no se vería.
 */
const HEAT_FULL_INTENSITY_ZOOM = 12;
const MARKER_SIZE_PX = 34;

function cssToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function HeatPointsLayer({ points }: { points: readonly HeatPoint[] }) {
  const map = useMap();
  useEffect(() => {
    // Los tipos del complemento están escritos para Leaflet 2; con Leaflet 1.9 es una capa normal.
    const layer = new HeatLayer(
      points.map((point): [number, number, number] => [point.lat, point.lon, point.u / U_MAX]),
      {
        radius: HEAT_RADIUS_PX,
        blur: HEAT_BLUR_PX,
        minOpacity: HEAT_MIN_OPACITY,
        max: 1,
        maxZoom: HEAT_FULL_INTENSITY_ZOOM,
        gradient: {
          0.2: cssToken("--color-heat-low"),
          0.6: cssToken("--color-heat-mid"),
          1: cssToken("--color-heat-high"),
        },
      },
    ) as unknown as Layer;
    map.addLayer(layer);
    return () => {
      map.removeLayer(layer);
    };
  }, [map, points]);
  return null;
}

/** Marcadores agrupados; cada uno muestra la U del reporte con número. */
function ReportMarkersLayer({ points }: { points: readonly HeatPoint[] }) {
  const map = useMap();
  useEffect(() => {
    const group = globalLeaflet.markerClusterGroup({ showCoverageOnHover: false });
    for (const point of points) {
      const score = formatScore(point.u);
      group.addLayer(
        marker([point.lat, point.lon], {
          title: `Urgencia U = ${score}`,
          icon: divIcon({
            className: "report-marker",
            html: score, // solo dígitos y coma: sale del formateador, no de datos escritos por personas
            iconSize: [MARKER_SIZE_PX, MARKER_SIZE_PX],
          }),
        }),
      );
    }
    group.addTo(map);
    return () => {
      group.remove();
    };
  }, [map, points]);
  return null;
}

type Props = {
  points: readonly HeatPoint[];
  /** Capa opcional «Ver reportes». */
  showReports: boolean;
};

/** Mapa de calor de los reportes activos evaluados (HU-08), centrado en Pasto. */
export function HeatMap({ points, showReports }: Props) {
  return (
    <BaseMap className="heat-map" label="Mapa de calor de reportes">
      <HeatPointsLayer points={points} />
      {showReports ? <ReportMarkersLayer points={points} /> : null}
    </BaseMap>
  );
}
