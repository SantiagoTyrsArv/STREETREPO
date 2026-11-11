import type { Severity } from "../../api/types";
import {
  formatDistance,
  formatScore,
  formatShortDate,
  formatWeight,
  severityLabel,
} from "../../format/format";
import type { AdminReport, Evaluation } from "./api";
import { highwayLabel } from "./labels";

/** Los factores van de 0 a 10; la barra solo dibuja esa proporción. */
const FACTOR_MAX = 10;
const PERCENT = 100;

type FactorProps = {
  symbol: "S" | "F" | "P";
  label: string;
  value: number;
  weight: number;
  /** La barra de S toma el color de la severidad declarada. */
  severity?: Severity;
};

function Factor({ symbol, label, value, weight, severity }: FactorProps) {
  return (
    <div className="factor" data-factor={symbol} data-severity={severity}>
      <div className="factor__line">
        <p>
          <strong>{symbol}</strong> <span>{label}</span>
        </p>
        <p className="factor__value">
          {formatScore(value)} × {formatWeight(weight)}
        </p>
      </div>
      <div className="factor__bar" aria-hidden="true">
        <div
          className="factor__fill"
          style={{ width: `${Math.min(PERCENT, (value / FACTOR_MAX) * PERCENT)}%` }}
        />
      </div>
    </div>
  );
}

function flowLabel(road: AdminReport["road"]): string {
  return road ? `Flujo · vía ${highwayLabel(road.highway)}` : "Flujo · sin vía asociada";
}

function proximityLabel(service: Evaluation["service"]): string {
  return service
    ? `Proximidad · ${service.service_type} a ${formatDistance(service.distance_m)}`
    : "Proximidad · ningún servicio crítico a menos de 500 m";
}

type Props = {
  evaluation: Evaluation | null;
  severity: Severity;
  road: AdminReport["road"];
};

/**
 * Desglose del cálculo de prioridad con los valores guardados por la API. El panel no
 * multiplica ni suma: muestra cada factor con su peso y la U que calculó el servidor.
 */
export function ScoreBreakdown({ evaluation, severity, road }: Props) {
  if (!evaluation) {
    return <p className="breakdown__pending">Pendiente de evaluación</p>;
  }
  const { w_severity: w1, w_flow: w2, w_proximity: w3 } = evaluation;
  return (
    <>
      <p className="card__hint">
        Pesos {formatWeight(w1)} / {formatWeight(w2)} / {formatWeight(w3)} · versión{" "}
        {evaluation.config_id}
      </p>
      <Factor
        symbol="S"
        label={`Severidad · ${severityLabel(severity).toLowerCase()}`}
        value={evaluation.s}
        weight={w1}
        severity={severity}
      />
      <Factor symbol="F" label={flowLabel(road)} value={evaluation.f} weight={w2} />
      <Factor
        symbol="P"
        label={proximityLabel(evaluation.service)}
        value={evaluation.p}
        weight={w3}
      />
      {evaluation.service?.name ? (
        <p className="card__hint">Servicio crítico más cercano: {evaluation.service.name}</p>
      ) : null}
      <div className="breakdown__total">
        <p>Urgencia U</p>
        <p>
          <span className="breakdown__score">{formatScore(evaluation.u)}</span>
          <span className="breakdown__scale"> / 10</span>
        </p>
      </div>
      <p className="card__hint">Calculado el {formatShortDate(evaluation.calculated_at)}</p>
    </>
  );
}
