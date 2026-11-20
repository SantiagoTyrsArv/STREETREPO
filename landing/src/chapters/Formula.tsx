import gsap from "gsap";
import { ScrambleTextPlugin } from "gsap/ScrambleTextPlugin";
import { useEffect, useRef, useState } from "react";
import { COPY } from "../content/copy";
import "./Formula.css";

gsap.registerPlugin(ScrambleTextPlugin);

/** Caracteres del descifrado: los de la propia fórmula, como una pantalla de datos. */
const SCRAMBLE_CHARS = "0123456789·=+SFPU";
/** Tramo en el que el relleno sube por dentro del contorno. */
const FILL_FROM = 0.06;
const FILL_TO = 0.2;

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

/** Fórmula con S, F y P resaltados (el azul del capítulo). */
function ColoredFormula({ text }: { text: string }) {
  return (
    <>
      {[...text].map((ch, i) =>
        "SFP".includes(ch) ? (
          <span key={i} className="formula__var">
            {ch}
          </span>
        ) : (
          ch
        ),
      )}
    </>
  );
}

/**
 * La fórmula de urgencia U: al entrar se descifra en contorno (caracteres de datos que se asientan)
 * y después el relleno sube por dentro; los factores aparecen uno a uno con el *scroll*.
 */
export function Formula({ progress, still }: FormulaProps) {
  const animated = useRef<HTMLSpanElement>(null);
  const [decoded, setDecoded] = useState(false);
  const started = progress >= FORMULA_FROM;

  useEffect(() => {
    const el = animated.current;
    // Una vez descifrada no se repite: ScrambleText reescribiría los S, F y P resaltados.
    if (still || !started || decoded || !el) return;
    const tween = gsap.to(el, {
      duration: 1.2,
      ease: "none",
      scrambleText: { text: COPY.formula, chars: SCRAMBLE_CHARS, revealDelay: 0.25, speed: 0.6 },
      onComplete: () => setDecoded(true),
    });
    return () => {
      tween.kill();
    };
  }, [still, started, decoded]);

  const style = (from: number) =>
    still
      ? undefined
      : {
          opacity: visibility(progress, from),
          transform: `translateY(${(1 - visibility(progress, from)) * 1.5}rem)`,
        };
  const fill = Math.min(
    1,
    Math.max(0, (progress - FORMULA_FROM - FILL_FROM) / (FILL_TO - FILL_FROM)),
  );

  return (
    <div className="formula">
      {still ? (
        <p className="formula__equation">{COPY.formula}</p>
      ) : (
        <p
          className="formula__equation formula__equation--stroke"
          style={{ ...style(FORMULA_FROM), ["--fill" as string]: `${Math.round(fill * 20) * 5}%` }}
        >
          <span className="visually-hidden">{COPY.formula}</span>
          {/* GSAP escribe el descifrado en este nodo; al terminar, React lo reemplaza entero (otra
              key) por la versión con S, F y P resaltados, sin pelear por el mismo texto. */}
          <span
            key={decoded ? "decoded" : "scramble"}
            ref={animated}
            className="formula__glyphs"
            aria-hidden="true"
          >
            {decoded ? <ColoredFormula text={COPY.formula} /> : COPY.formula}
          </span>
        </p>
      )}
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
