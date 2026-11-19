import { COPY } from "../content/copy";
import "./Formula.css";

interface FormulaProps {
  progress: number;
  still: boolean;
}

/** Desde qué progreso del capítulo se construye la fórmula y cada factor. */
const FORMULA_FROM = 0.38;
const FACTOR_STEP = 0.08;

function visibility(progress: number, from: number): number {
  return Math.min(1, Math.max(0, (progress - from) / 0.08));
}

/** La fórmula de urgencia U y sus factores, que aparecen uno a uno con el *scroll*. */
export function Formula({ progress, still }: FormulaProps) {
  const style = (from: number) =>
    still
      ? undefined
      : {
          opacity: visibility(progress, from),
          transform: `translateY(${(1 - visibility(progress, from)) * 1.5}rem)`,
        };
  return (
    <div className="formula">
      <p className="formula__equation" style={style(FORMULA_FROM)}>
        {COPY.formula}
      </p>
      <dl className="formula__factors">
        {COPY.factors.map((factor, i) => (
          <div
            key={factor.symbol}
            className="formula__factor"
            style={style(FORMULA_FROM + FACTOR_STEP * (i + 1))}
          >
            <dt>
              <span className="formula__symbol">{factor.symbol}</span> {factor.name}
            </dt>
            <dd>{factor.description}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
