import { useId, useState } from "react";
import { EmptyView, ErrorView, LoadingView } from "../../components/StateViews";
import { useRoundResults, useRounds, type Round, type RoundResults, type ZoneResult } from "./api";
import { BetweenZonesCard, TEST_LABELS } from "./BetweenZonesCard";
import { DedupTable } from "./DedupTable";
import { EXPORTS, useDownload } from "./exportLinks";
import { concentrationLabel } from "./labels";
import { formatPercent, formatPosition, formatPValue, formatShift } from "./resultsFormat";
import { ZoneAgreementCard } from "./ZoneAgreementCard";

const LOAD_PROBLEM = "No pudimos cargar los resultados. Inténtalo de nuevo.";
export const RESULTS_NOTE =
  "Estos valores describen la ronda; la interpretación de las hipótesis se hace en la tesis.";

function ExportButtons({ round }: { round: Round }) {
  const { download, pending, problem } = useDownload(round.id);
  return (
    <div className="result-exports">
      <div className="page__actions">
        {EXPORTS.map((item) => (
          <button
            key={item.kind}
            type="button"
            className={item.primary ? "button" : "button button--outline"}
            disabled={pending !== null}
            onClick={() => void download(item.kind)}
          >
            {pending === item.kind ? "Descargando…" : item.label}
          </button>
        ))}
      </div>
      {problem ? (
        <div className="alert" role="alert">
          <span className="alert__icon" aria-hidden="true">
            !
          </span>
          <p>{problem}</p>
        </div>
      ) : null}
    </div>
  );
}

/** Cifras principales (Figma «Cifras»): coincidencia ±1 por zona y la prueba entre zonas. */
function Figures({ results }: { results: RoundResults }) {
  const between = results.between;
  return (
    <section className="result-figures" aria-label={`Cifras de la ronda «${results.round.name}»`}>
      {results.zones.map((zone) =>
        zone.agreement ? (
          <div key={zone.zone_id} className="card result-figure">
            <p className="result-figure__value">{formatPercent(zone.agreement.within_one_pct)}</p>
            <p className="result-figure__label">
              Coincidencia ±1 · {zone.name} ({concentrationLabel(zone.concentration).toLowerCase()})
            </p>
          </div>
        ) : null,
      )}
      <div className="card result-figure">
        <p className="result-figure__value">
          {between.computable && typeof between.p_value === "number"
            ? formatPValue(between.p_value)
            : "—"}
        </p>
        <p className="result-figure__label">
          {between.computable
            ? `Prueba ${TEST_LABELS[between.test ?? ""] ?? ""}`
            : "Prueba entre zonas: no calculada"}
        </p>
      </div>
    </section>
  );
}

function ZonesTable({ zones }: { zones: readonly ZoneResult[] }) {
  const titleId = useId();
  return (
    <section className="card result-card" aria-labelledby={titleId}>
      <h3 className="validation-title result-card__title" id={titleId}>
        Zonas muestreadas
      </h3>
      <table className="data-table" aria-label="Zonas muestreadas">
        <thead>
          <tr>
            <th scope="col">Zona</th>
            <th scope="col">Concentración</th>
            <th scope="col" className="data-table__number">
              Reportes
            </th>
            <th scope="col" className="data-table__number">
              Evaluadores
            </th>
            <th scope="col">Coincidencia ±1</th>
          </tr>
        </thead>
        <tbody>
          {zones.map((zone) => (
            <tr key={zone.zone_id}>
              <td>{zone.name}</td>
              <td>{zone.concentration === "alta" ? "Alta" : "Baja"}</td>
              <td className="data-table__number">{zone.n_reports}</td>
              <td className="data-table__number">{zone.agreement?.n_evaluators ?? 0}</td>
              <td>
                {zone.agreement ? (
                  <span className="result-chip">
                    {formatPercent(zone.agreement.within_one_pct)}
                  </span>
                ) : (
                  "Sin órdenes"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

/** Ranking comparado (Figma): orden del motor y del panel en una zona, reporte por reporte. */
function ComparedRanking({ zones }: { zones: readonly ZoneResult[] }) {
  const titleId = useId();
  const withOrders = zones.filter((zone) => zone.agreement !== null);
  const [selectedId, setSelectedId] = useState<number | undefined>(withOrders[0]?.zone_id);
  const zone = withOrders.find((item) => item.zone_id === selectedId) ?? withOrders[0];

  return (
    <section className="card result-card" aria-labelledby={titleId}>
      <div className="result-card__head">
        <h3 className="validation-title result-card__title" id={titleId}>
          Ranking comparado{zone ? ` · zona ${zone.name}` : ""}
        </h3>
        {withOrders.length > 1 ? (
          <div className="segmented" role="group" aria-label="Zona del ranking comparado">
            {withOrders.map((item) => (
              <button
                key={item.zone_id}
                type="button"
                className="segmented__option"
                aria-pressed={item.zone_id === zone?.zone_id}
                onClick={() => setSelectedId(item.zone_id)}
              >
                {item.name}
              </button>
            ))}
          </div>
        ) : null}
      </div>
      {zone ? (
        <table className="data-table" aria-label={`Ranking comparado · zona ${zone.name}`}>
          <thead>
            <tr>
              <th scope="col">Reporte</th>
              <th scope="col" className="data-table__number">
                Motor
              </th>
              <th scope="col" className="data-table__number">
                Panel
              </th>
              <th scope="col">Diferencia</th>
            </tr>
          </thead>
          <tbody>
            {zone.reports.map((report) => (
              <tr key={report.report_id}>
                <td>{report.road_name ?? "Vía sin nombre"}</td>
                <td className="data-table__number">{report.motor_order}</td>
                <td className="data-table__number">
                  {report.panel_order === null ? "—" : formatPosition(report.panel_order)}
                </td>
                <td>
                  {report.panel_order === null ? null : (
                    <span
                      className={`result-chip${report.panel_order === report.motor_order ? " result-chip--same" : " result-chip--shift"}`}
                    >
                      {formatShift(report.motor_order, report.panel_order)}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Ninguna zona tiene órdenes de los evaluadores.</p>
      )}
      <p className="card__hint">
        Panel: posición media de los evaluadores convertida en rangos (los empates quedan como
        rangos promedio). ▼ el panel lo ubica más abajo; ▲, más arriba.
      </p>
    </section>
  );
}

function Results({ round }: { round: Round }) {
  const results = useRoundResults(round.id);
  if (results.isPending) {
    return <LoadingView label="Calculando los resultados…" />;
  }
  if (results.isError) {
    return <ErrorView message={LOAD_PROBLEM} onRetry={() => void results.refetch()} />;
  }
  const data = results.data;
  return (
    <div className="results">
      <Figures results={data} />
      <div className="result-columns">
        <ZonesTable zones={data.zones} />
        <ComparedRanking key={round.id} zones={data.zones} />
      </div>
      <div className="result-columns">
        {data.zones.map((zone) => (
          <ZoneAgreementCard key={zone.zone_id} zone={zone} />
        ))}
      </div>
      <BetweenZonesCard between={data.between} />
      <DedupTable zones={data.zones} />
      <p className="result-note">{RESULTS_NOTE}</p>
    </div>
  );
}

/** Resultados de una ronda cerrada y sus exportaciones (objetivo 4, ADR 0008). */
export function ResultsPanel() {
  const rounds = useRounds();
  const selectId = useId();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (rounds.isPending) {
    return <LoadingView label="Cargando las rondas…" />;
  }
  if (rounds.isError) {
    return <ErrorView message={LOAD_PROBLEM} onRetry={() => void rounds.refetch()} />;
  }
  const closed = rounds.data.filter((round) => round.status === "cerrada");
  if (closed.length === 0) {
    return rounds.data.length > 0 ? (
      <EmptyView
        title="Los resultados se muestran al cerrar la ronda."
        detail="Mientras está abierta, las métricas no se calculan para no influir en el panel."
      />
    ) : (
      <EmptyView
        title="Aún no hay rondas cerradas"
        detail="Abre y cierra una ronda en la pestaña Rondas."
      />
    );
  }
  const round = closed.find((item) => item.id === selectedId) ?? closed[0]!;

  return (
    <div className="results">
      <div className="result-toolbar">
        {closed.length > 1 ? (
          <div className="field">
            <label htmlFor={selectId}>Ronda</label>
            <select
              id={selectId}
              className="select"
              value={round.id}
              onChange={(event) => setSelectedId(event.target.value)}
            >
              {closed.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
        ) : (
          <p className="validation-title">Ronda «{round.name}»</p>
        )}
        <ExportButtons round={round} />
      </div>
      <Results key={round.id} round={round} />
    </div>
  );
}
