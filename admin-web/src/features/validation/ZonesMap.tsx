import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import { BaseMap } from "../../map/BaseMap";
import { useZones, type Concentration } from "./api";
import { concentrationLabel } from "./labels";
import { ZonePolygons } from "./ZonePolygons";

const LOAD_PROBLEM = "No pudimos cargar las zonas. Inténtalo de nuevo.";
const CONCENTRATIONS: readonly Concentration[] = ["alta", "baja"];

/** El color de la zona siempre va con su texto (guía 10.3): leyenda y columna de la tabla. */
function ConcentrationLegend() {
  return (
    <div className="zone-legend" role="group" aria-label="Concentración de reportes">
      {CONCENTRATIONS.map((concentration) => (
        <span key={concentration} className="zone-legend__item">
          <span
            className={`zone-legend__swatch zone-legend__swatch--${concentration}`}
            aria-hidden="true"
          />
          {concentrationLabel(concentration)}
        </span>
      ))}
    </div>
  );
}

/** Zonas del estudio (objetivo 4): mapa con los polígonos y tabla con sus reportes. */
export function ZonesMap() {
  const zones = useZones();

  if (zones.isPending) {
    return <LoadingView label="Cargando las zonas…" />;
  }
  if (zones.isError) {
    return <ErrorView message={LOAD_PROBLEM} onRetry={() => void zones.refetch()} />;
  }
  if (zones.data.length === 0) {
    return (
      <EmptyView
        title="Aún no hay zonas"
        detail="El administrador del sistema las define en un GeoJSON: cárgalas con zones-import (README, «Validación con el panel de referencia»)."
      />
    );
  }

  return (
    <div className="zones">
      <section className="card">
        <div className="card__header">
          <h2 className="card__title">Mapa de las zonas</h2>
          <ConcentrationLegend />
        </div>
        <BaseMap label="Mapa de las zonas del estudio" className="zones__map">
          <ZonePolygons zones={zones.data} />
        </BaseMap>
      </section>

      <section className="card">
        <table className="data-table" aria-label="Zonas del estudio">
          <thead>
            <tr>
              <th scope="col">Zona</th>
              <th scope="col">Concentración</th>
              <th scope="col" className="data-table__number">
                Reportes activos
              </th>
              <th scope="col" className="data-table__number">
                Reportes en total
              </th>
            </tr>
          </thead>
          <tbody>
            {zones.data.map((zone) => (
              <tr key={zone.id}>
                <td>{zone.name}</td>
                <td>{concentrationLabel(zone.concentration)}</td>
                <td className="data-table__number">{zone.active_reports}</td>
                <td className="data-table__number">{zone.total_reports}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="card__note">
          Activos: todo estado salvo Reparado. Para abrir una ronda, cada zona necesita al menos 5
          reportes activos con su urgencia calculada.
        </p>
      </section>
    </div>
  );
}
