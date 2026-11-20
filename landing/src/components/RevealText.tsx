import gsap from "gsap";
import { SplitText } from "gsap/SplitText";
import { Fragment, useLayoutEffect, useRef, useState, type ElementType } from "react";
import { useProximity, type ProximityAxes } from "../text/ProximityText";
import { useWarp } from "../text/useWarp";
import "./RevealText.css";

gsap.registerPlugin(SplitText);

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
  /** Por líneas desde una máscara (títulos) o por palabras (textos de apoyo). */
  split?: "lines" | "words";
}

function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/**
 * Avance (0–1) de la parte `i` de `count` dentro del tramo: cada parte empieza un 40 % de su
 * duración después de la anterior y la última termina justo en `to`.
 */
function partProgress(progress: number, from: number, to: number, i: number, count: number) {
  const duration = (to - from) / (1 + 0.4 * (count - 1));
  return clamp01((progress - from - i * duration * 0.4) / duration);
}

const TITLE_TAGS = new Set(["h1", "h2", "h3"]);

/**
 * Texto que entra ligado al progreso del *scroll*: por líneas (cada línea sube desde una máscara
 * con un leve giro y desenfoque; SplitText las reparte de nuevo si cambia el ancho) o por palabras.
 * Los títulos además se deforman cerca del puntero (*warp*).
 */
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
  split = "lines",
}: RevealTextProps) {
  const ref = useRef<HTMLElement>(null);
  const lines = useRef<HTMLElement[]>([]);
  const [version, setVersion] = useState(0);
  const byLines = split === "lines" && !still;
  useProximity(ref, {
    selector: ".reveal__word",
    axes: proximity ?? { wght: [400, 400] },
    enabled: Boolean(proximity) && !still,
  });
  useWarp(ref, !still && typeof Tag === "string" && TITLE_TAGS.has(Tag), version);

  const place = (value: number) => {
    const count = lines.current.length;
    lines.current.forEach((line, i) => {
      const local = partProgress(value, from, to, i, count);
      line.style.transform = `translateY(${Math.round((1 - local) * 110)}%) rotate(${((1 - local) * 4).toFixed(2)}deg)`;
      line.style.filter = local < 1 ? `blur(${((1 - local) * 6).toFixed(2)}px)` : "";
    });
  };
  const placeRef = useRef(place);
  placeRef.current = place;

  useLayoutEffect(() => {
    const el = ref.current;
    if (!byLines || !el) return;
    const splitter = SplitText.create(el, {
      type: "lines,words",
      mask: "lines",
      linesClass: "reveal__line",
      wordsClass: "reveal__word",
      autoSplit: true,
      onSplit(self) {
        lines.current = self.lines as HTMLElement[];
        placeRef.current(progressRef.current);
        setVersion((v) => v + 1);
      },
    });
    return () => {
      splitter.revert();
      lines.current = [];
    };
  }, [byLines, text]);

  const progressRef = useRef(progress);
  progressRef.current = progress;
  useLayoutEffect(() => {
    if (byLines) placeRef.current(progress);
  }, [byLines, progress]);

  const classes = ["reveal", className].filter(Boolean).join(" ");
  if (still || byLines) {
    return (
      <Tag ref={ref} id={id} className={classes}>
        {text}
      </Tag>
    );
  }
  const words = text.split(" ");
  return (
    <Tag ref={ref} id={id} className={classes}>
      {words.map((word, i) => {
        const local = partProgress(progress, from, to, i, words.length);
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
