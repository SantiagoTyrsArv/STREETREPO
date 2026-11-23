import { useId } from "react";
import type { components } from "../../api/schema";
import type { ZoneResult } from "./api";
import { concentrationLabel } from "./labels";
import { formatCoefficient, formatPercent, formatPValue } from "./resultsFormat";

type Correlation = components["schemas"]["CorrelationResponse"];

const NOT_DEFINED = "No definible";

function Statistic({ label, value }: { label: string; value: Correlation | null }) {
  return (
    <>
      <dt>{label}</dt>
      <dd>
        {value === null ? (
          NOT_DEFINED
        ) : (
          <>
            {formatCoefficient(value.coefficient)}
            <span className="metric__p">{formatPValue(value.p_value)}</span>
          </>
        )}
      </dd>
    </>
  );
}

/** Acuerdo entre el orden del motor y el del panel en una zona (propuesta 114). */
export function ZoneAgreementCard({ zone }: { zone: ZoneResult }) {
  const titleId = useId();
  const { agreement } = zone;

  return (
    <section className="card result-card" aria-labelledby={titleId}>
      <h3 className="validation-title result-card__title" id={titleId}>
        Acuerdo en {zone.name}
      </h3>
      <p className="card__hint">
        {concentrationLabel(zone.concentration)} · {zone.n_reports} reportes
      </p>
      {agreement === null ? (
        <p>Ningún evaluador envió el orden de esta zona.</p>
      ) : (
        <>
          <dl className="metrics">
            <dt>Evaluadores</dt>
            <dd>{agreement.n_evaluators}</dd>
            <Statistic label="rho de Spearman" value={agreement.spearman} />
            <Statistic label="tau-b de Kendall" value={agreement.kendall} />
            <dt>W de Kendall</dt>
            <dd>
              {agreement.kendall_w === null ? (
                "Se necesitan al menos 2 evaluadores"
              ) : (
                <>
                  {formatCoefficient(agreement.kendall_w.w)}
                  <span className="metric__p">{formatPValue(agreement.kendall_w.p_value)}</span>
                </>
              )}
            </dd>
            <dt>Coincidencia ±1</dt>
            <dd>{formatPercent(agreement.within_one_pct)}</dd>
          </dl>
          <table className="data-table" aria-label={`Acuerdo de cada evaluador en ${zone.name}`}>
            <thead>
              <tr>
                <th scope="col">Evaluador</th>
                <th scope="col">rho de Spearman</th>
                <th scope="col">tau-b de Kendall</th>
              </tr>
            </thead>
            <tbody>
              {agreement.per_evaluator.map((row) => (
                <tr key={row.evaluator}>
                  <td>{row.evaluator}</td>
                  <td>
                    {row.spearman
                      ? `${formatCoefficient(row.spearman.coefficient)} (${formatPValue(row.spearman.p_value)})`
                      : NOT_DEFINED}
                  </td>
                  <td>
                    {row.kendall
                      ? `${formatCoefficient(row.kendall.coefficient)} (${formatPValue(row.kendall.p_value)})`
                      : NOT_DEFINED}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
