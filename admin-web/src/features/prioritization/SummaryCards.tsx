import type { Summary } from "./api";

const CARDS: ReadonlyArray<{ key: keyof Summary; label: string }> = [
  { key: "active", label: "Activos" },
  { key: "evaluated", label: "Evaluados" },
  { key: "prioritized", label: "Priorizados" },
  { key: "repaired", label: "Reparados" },
];

const NO_VALUE = "—";

/** Indicadores del encabezado: conteos por estado que da la API (propuesta 75). */
export function SummaryCards({ summary }: { summary: Summary | undefined }) {
  return (
    <ul className="summary" aria-label="Reportes por estado">
      {CARDS.map(({ key, label }) => (
        <li key={key} className="summary__card">
          <span className="summary__label">{label}</span>
          <span className="summary__value">{summary ? summary[key] : NO_VALUE}</span>
        </li>
      ))}
    </ul>
  );
}
