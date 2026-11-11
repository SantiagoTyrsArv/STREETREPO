import { useId, useState, type FormEvent } from "react";
import { formatScore } from "../../format/format";
import type { WeightsInput, WeightVersion } from "./api";
import {
  hundredthsToApi,
  sumHundredths,
  toHundredths,
  WEIGHT_TOTAL_HUNDREDTHS,
} from "./parseWeight";

const HUNDREDTHS_PER_UNIT = 100;
/** Valores iniciales del modelo (guía 2.2), en centésimas. */
const DEFAULT_HUNDREDTHS = { w_severity: 50, w_flow: 30, w_proximity: 20 } as const;

type Key = keyof WeightsInput;

const CONTROLS: ReadonlyArray<{ key: Key; symbol: string; label: string }> = [
  { key: "w_severity", symbol: "w₁", label: "Severidad (S)" },
  { key: "w_flow", symbol: "w₂", label: "Flujo vehicular (F)" },
  { key: "w_proximity", symbol: "w₃", label: "Proximidad a servicios críticos (P)" },
];

const INVALID_WEIGHT_MESSAGE =
  "Escribe un número entre 0 y 1 con máximo dos decimales, por ejemplo 0,25.";

/** Centésimas → texto de la interfaz, con coma (50 → «0,50»). */
function display(hundredths: number): string {
  return formatScore(hundredths / HUNDREDTHS_PER_UNIT);
}

/** Los pesos de la API tienen dos decimales exactos; se pasan a centésimas enteras. */
function fromApi(weight: number): number {
  return Math.round(weight * HUNDREDTHS_PER_UNIT);
}

type Props = {
  /** Versión vigente, de la que parte la edición. */
  current: WeightVersion;
  saving: boolean;
  onSave: (weights: WeightsInput) => void;
};

/**
 * Edición de w₁, w₂ y w₃ (HU-14). Acepta coma decimal y bloquea guardar si algún peso no es
 * válido o si no suman 1,00; el servidor vuelve a validar.
 */
export function WeightsForm({ current, saving, onSave }: Props) {
  const baseId = useId();
  const initial: Record<Key, number> = {
    w_severity: fromApi(current.w_severity),
    w_flow: fromApi(current.w_flow),
    w_proximity: fromApi(current.w_proximity),
  };
  const [texts, setTexts] = useState<Record<Key, string>>({
    w_severity: display(initial.w_severity),
    w_flow: display(initial.w_flow),
    w_proximity: display(initial.w_proximity),
  });

  const values = CONTROLS.map(({ key }) => toHundredths(texts[key]));
  const total = sumHundredths(CONTROLS.map(({ key }) => texts[key]));
  const sumsToOne = total === WEIGHT_TOTAL_HUNDREDTHS;
  const unchanged = CONTROLS.every(({ key }, index) => values[index] === initial[key]);
  const canSave = sumsToOne && !unchanged && !saving;

  function setText(key: Key, text: string) {
    setTexts((previous) => ({ ...previous, [key]: text }));
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const [w1, w2, w3] = values;
    if (!canSave || w1 == null || w2 == null || w3 == null) {
      return;
    }
    onSave({
      w_severity: hundredthsToApi(w1),
      w_flow: hundredthsToApi(w2),
      w_proximity: hundredthsToApi(w3),
    });
  }

  return (
    <form className="weights-form" onSubmit={handleSubmit}>
      {CONTROLS.map(({ key, symbol, label }, index) => {
        const value = values[index] ?? null;
        const inputId = `${baseId}-${key}`;
        const errorId = `${inputId}-error`;
        return (
          <div key={key} className="weight-control">
            <div className="weight-control__line">
              <label htmlFor={inputId}>
                <strong>{symbol}</strong> {label}
              </label>
              <input
                id={inputId}
                className="weight-control__input"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                value={texts[key]}
                aria-invalid={value === null}
                aria-describedby={value === null ? errorId : undefined}
                onChange={(event) => setText(key, event.target.value)}
              />
            </div>
            <input
              className="weight-control__slider"
              type="range"
              min={0}
              max={WEIGHT_TOTAL_HUNDREDTHS}
              step={1}
              value={value ?? 0}
              aria-label={`${symbol} ${label}, deslizador`}
              aria-valuetext={value === null ? undefined : display(value)}
              onChange={(event) => setText(key, display(Number(event.target.value)))}
            />
            {value === null ? (
              <p id={errorId} className="weight-control__error">
                {INVALID_WEIGHT_MESSAGE}
              </p>
            ) : null}
          </div>
        );
      })}

      <div className="weights-sum" data-ok={sumsToOne}>
        {sumsToOne ? (
          <p>Los pesos suman 1,00</p>
        ) : (
          <p role="alert">
            {total === null
              ? "Corrige los pesos marcados para ver la suma."
              : `Los pesos suman ${display(total)}. Deben sumar exactamente 1,00.`}
          </p>
        )}
        <p className="weights-sum__total">Σ = {total === null ? "—" : display(total)}</p>
      </div>

      <div className="weights-form__actions">
        <button type="submit" className="button" disabled={!canSave}>
          {saving ? "Guardando…" : "Guardar y recalcular puntajes"}
        </button>
        <button
          type="button"
          className="button button--outline"
          disabled={saving}
          onClick={() =>
            setTexts({
              w_severity: display(DEFAULT_HUNDREDTHS.w_severity),
              w_flow: display(DEFAULT_HUNDREDTHS.w_flow),
              w_proximity: display(DEFAULT_HUNDREDTHS.w_proximity),
            })
          }
        >
          Restaurar 0,5 / 0,3 / 0,2
        </button>
      </div>
    </form>
  );
}
