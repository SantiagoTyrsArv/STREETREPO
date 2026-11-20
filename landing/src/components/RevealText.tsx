import { Fragment, useRef, type ElementType } from "react";
import { useProximity, type ProximityAxes } from "../text/ProximityText";
import "./RevealText.css";

interface RevealTextProps {
  text: string;
  /** Progreso del capítulo (0–1). */
  progress: number;
  /** Tramo del progreso en el que entra el texto. */
  from: number;
  to: number;
  as?: ElementType;
  id?: string;
  className?: string;
  /** Sin animación: el texto aparece completo. */
  still?: boolean;
  /** *Variable proximity* por palabra (textos de apoyo). */
  proximity?: ProximityAxes;
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/** Texto que entra palabra por palabra desde una máscara, ligado al progreso del *scroll*. */
export function RevealText({
  text,
  progress,
  from,
  to,
  as: Tag = "p",
  id,
  className,
  still,
  proximity,
}: RevealTextProps) {
  const ref = useRef<HTMLElement>(null);
  useProximity(ref, {
    selector: ".reveal__word",
    axes: proximity ?? { wght: [400, 400] },
    enabled: Boolean(proximity) && !still,
  });
  const classes = ["reveal", className].filter(Boolean).join(" ");
  if (still) {
    return (
      <Tag id={id} className={classes}>
        {text}
      </Tag>
    );
  }
  const words = text.split(" ");
  const span = (to - from) / words.length;
  return (
    <Tag ref={ref} id={id} className={classes}>
      {words.map((word, i) => {
        const local = clamp01((progress - from - i * span * 0.6) / (span * 2));
        return (
          <Fragment key={`${word}-${i}`}>
            <span className="reveal__mask">
              <span
                className="reveal__word"
                style={{ transform: `translateY(${(1 - local) * 110}%)` }}
              >
                {word}
              </span>
            </span>
            {i < words.length - 1 ? " " : null}
          </Fragment>
        );
      })}
    </Tag>
  );
}
