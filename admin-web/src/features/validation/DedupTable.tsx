import { useId } from "react";
import type { ZoneResult } from "./api";

/** Deduplicación de cada zona: todos sus reportes y los avisos de «Posible duplicado» (8.1). */
export function DedupTable({ zones }: { zones: readonly ZoneResult[] }) {
  const titleId = useId();
  return (
    <section className="card result-card" aria-labelledby={titleId}>
      <h3 className="validation-title result-card__title" id={titleId}>
        Deduplicación
      </h3>
      <table className="data-table" aria-label="Deduplicación por zona">
        <thead>
          <tr>
            <th scope="col">Zona</th>
            <th scope="col" className="data-table__number">
              Reportes
            </th>
            <th scope="col" className="data-table__number">
              Con confirmación
            </th>
            <th scope="col" className="data-table__number">
              Confirmaciones
            </th>
            <th scope="col" className="data-table__number">
              Avisos
            </th>
            <th scope="col" className="data-table__number">
              Confirmó
            </th>
            <th scope="col" className="data-table__number">
              Creó igual
            </th>
            <th scope="col" className="data-table__number">
              Sin decisión
            </th>
          </tr>
        </thead>
        <tbody>
          {zones.map(({ zone_id, name, dedup }) => (
            <tr key={zone_id}>
              <td>{name}</td>
              <td className="data-table__number">{dedup.reports}</td>
              <td className="data-table__number">{dedup.reports_confirmed}</td>
              <td className="data-table__number">{dedup.confirmations}</td>
              <td className="data-table__number">{dedup.warnings_total}</td>
              <td className="data-table__number">{dedup.warnings_confirmed}</td>
              <td className="data-table__number">{dedup.warnings_created_anyway}</td>
              <td className="data-table__number">{dedup.warnings_pending}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="card__note">
        Todos los reportes de cada zona, no solo la muestra. Los avisos se registran desde la
        migración 0009; la revisión manual de duplicados se hace con los CSV de reportes y avisos.
      </p>
    </section>
  );
}
