import { useId, useState } from "react";
import { COPY } from "../content/copy";
import { ProximityText } from "../text/ProximityText";
import { KICKER_AXES } from "../text/proximity";
import {
  DEFAULT_WEIGHTS,
  flowScore,
  formatDecimal,
  proximityScore,
  severityScore,
  urgency,
  type RoadKind,
  type Severity,
} from "./urgency";
import "./Calculator.css";

/** Estado inicial: el reporte «Av. Los Estudiantes» de la tabla de la guía (U = 8,70). */
const INITIAL = { severity: "alta" as Severity, road: "secundaria" as RoadKind, distance: 180 };
const MAX_DISTANCE = 600;
const STEP = 10;

/** «Pruébalo»: calculadora de urgencia en vivo con las reglas reales del modelo. */
export function Calculator() {
  const copy = COPY.calculadora;
  const id = useId();
  const [severity, setSeverity] = useState<Severity>(INITIAL.severity);
  const [road, setRoad] = useState<RoadKind>(INITIAL.road);
  const [distance, setDistance] = useState(INITIAL.distance);

  const s = severityScore(severity);
  const f = flowScore(road);
  const p = proximityScore(distance);
  const u = urgency({ s, f, p });
  const w = DEFAULT_WEIGHTS;

  return (
    <section
      id="prueba"
      className="calc"
      aria-labelledby={`${id}-titulo`}
      data-accent="signal"
      data-ambient="visible"
    >
      <div className="calc__intro">
        <ProximityText
          as="p"
          className="calc__kicker"
          text={copy.kicker}
          by="char"
          axes={KICKER_AXES}
        />
        <h2 id={`${id}-titulo`} className="calc__title">
          {copy.title}
        </h2>
        <p className="calc__lead">{copy.lead}</p>
      </div>

      <div className="calc__panel">
        <form className="calc__controls" onSubmit={(e) => e.preventDefault()}>
          <fieldset className="calc__field">
            <legend>{copy.severityLabel}</legend>
            <div className="calc__options">
              {copy.severities.map((option) => (
                <label key={option.value} className="calc__option">
                  <input
                    type="radio"
                    name={`${id}-severidad`}
                    value={option.value}
                    checked={severity === option.value}
                    onChange={() => setSeverity(option.value)}
                  />
                  <span>{option.label}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="calc__field">
            <label htmlFor={`${id}-via`}>{copy.roadLabel}</label>
            <select
              id={`${id}-via`}
              value={road}
              onChange={(e) => setRoad(e.target.value as RoadKind)}
            >
              {copy.roads.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="calc__field">
            <label htmlFor={`${id}-distancia`}>
              {copy.distanceLabel}: <strong>{distance} m</strong>
            </label>
            <input
              id={`${id}-distancia`}
              type="range"
              min={0}
              max={MAX_DISTANCE}
              step={STEP}
              value={distance}
              aria-valuetext={`${distance} m`}
              onChange={(e) => setDistance(Number(e.target.value))}
            />
          </div>
        </form>

        <div className="calc__result">
          <p className="calc__result-label">{copy.resultLabel}</p>
          {/* Solo la urgencia (y la marca de vía) se anuncia: el desglose y la nota se leen al
              recorrer la página, no en cada paso del deslizador. */}
          <div role="status">
            <p className="calc__u">
              <span>{formatDecimal(u)}</span>
              <small> / 10</small>
            </p>
            {road === "sin-via" ? <p className="calc__flag">{copy.reviewRoad}</p> : null}
          </div>
          <div className="calc__bar" aria-hidden="true">
            <span style={{ width: `${u * 10}%` }} />
          </div>
          <p className="calc__breakdown">
            {formatDecimal(w.s).replace(/0$/, "")} · {s} + {formatDecimal(w.f).replace(/0$/, "")} ·{" "}
            {f} + {formatDecimal(w.p).replace(/0$/, "")} · {formatDecimal(p)} = {formatDecimal(u)}
          </p>
          <p className="calc__note">{copy.note}</p>
        </div>
      </div>
    </section>
  );
}
