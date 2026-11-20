import gsap from "gsap";
import { useEffect, useRef, type ElementType, type RefObject } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { damp } from "../interaction/motion";
import { pointer, startPointerTracking } from "../interaction/pointer";
import { trackVisibility } from "../interaction/visibility";
import { falloff } from "./proximity";
import "./ProximityText.css";

type Range = readonly [number, number];

export interface ProximityAxes {
  /** Grosor en reposo y bajo el puntero. */
  wght: Range;
  /** Ancho en reposo y bajo el puntero (solo fuentes con eje `wdth`, como Archivo). */
  wdth?: Range;
}

interface ProximityTextProps {
  text: string;
  /** Por letra (textos cortos) o por palabra (párrafos: menos nodos y sin saltos de línea). */
  by: "char" | "word";
  axes: ProximityAxes;
  as?: ElementType;
  className?: string;
  id?: string;
}

/** Respuesta del grosor (1/s): ágil al acercarse, sin parpadeos. */
const PROXIMITY_LAMBDA = 8;

function settings(axes: ProximityAxes, t: number): string {
  const wght = Math.round(axes.wght[0] + (axes.wght[1] - axes.wght[0]) * t);
  if (!axes.wdth) return `"wght" ${wght}`;
  const wdth = Math.round(axes.wdth[0] + (axes.wdth[1] - axes.wdth[0]) * t);
  return `"wght" ${wght}, "wdth" ${wdth}`;
}

function split(text: string, by: "char" | "word"): string[] {
  return by === "word" ? text.split(" ") : [...text];
}

/**
 * Aplica *variable proximity* a las partes de `ref` que cumplen `selector` (letras o palabras ya
 * partidas): cada una se engrosa (y se ensancha) cuanto más cerca está el puntero o el dedo
 * apoyado, y vuelve exactamente al reposo al alejarse o soltar.
 */
export function useProximity(
  ref: RefObject<HTMLElement>,
  { selector, axes, enabled }: { selector: string; axes: ProximityAxes; enabled: boolean },
): void {
  const axesKey = JSON.stringify(axes);
  useEffect(() => {
    const root = ref.current;
    if (!enabled || !root) return;
    const ax = JSON.parse(axesKey) as ProximityAxes;
    const rest = settings(ax, 0);
    const parts = [...root.querySelectorAll<HTMLElement>(selector)];
    if (parts.length === 0) return;
    const stopTracking = startPointerTracking();
    const view = trackVisibility(root);
    // Centros de cada parte respecto al contenedor: se miden al montar y al cambiar el tamaño, no
    // en cada cuadro (en cada cuadro solo se lee la posición del contenedor).
    let centers: { x: number; y: number }[] = [];
    const measure = () => {
      const box = root.getBoundingClientRect();
      centers = parts.map((part) => {
        const r = part.getBoundingClientRect();
        return { x: r.left + r.width / 2 - box.left, y: r.top + r.height / 2 - box.top };
      });
    };
    measure();
    window.addEventListener("resize", measure, { passive: true });
    const amount = parts.map(() => 0);
    const written = parts.map(() => rest);
    parts.forEach((part) => {
      part.style.fontVariationSettings = rest;
    });

    const tick = (_time: number, deltaMs: number) => {
      if (!view.visible) return;
      if (!pointer.active && amount.every((a) => a === 0)) return;
      const dt = Math.min(deltaMs / 1000, 0.1);
      const box = root.getBoundingClientRect();
      const px = ((pointer.x + 1) / 2) * window.innerWidth;
      const py = ((pointer.y + 1) / 2) * window.innerHeight;
      parts.forEach((part, i) => {
        const c = centers[i];
        if (!c) return;
        const goal = pointer.active
          ? falloff(Math.hypot(box.left + c.x - px, box.top + c.y - py))
          : 0;
        let next = damp(amount[i] as number, goal, PROXIMITY_LAMBDA, dt);
        if (goal === 0 && next < 0.001) next = 0;
        amount[i] = next;
        const value = settings(ax, next);
        if (value !== written[i]) {
          written[i] = value;
          part.style.fontVariationSettings = value;
        }
      });
    };
    gsap.ticker.add(tick);

    return () => {
      gsap.ticker.remove(tick);
      stopTracking();
      view.stop();
      window.removeEventListener("resize", measure);
      parts.forEach((part) => {
        part.style.fontVariationSettings = "";
      });
    };
  }, [ref, selector, axesKey, enabled]);
}

/**
 * Texto con *variable proximity*. El lector de pantalla recibe el texto completo una sola vez; las
 * partes son decorativas.
 */
export function ProximityText({
  text,
  by,
  axes,
  as: Tag = "span",
  className,
  id,
}: ProximityTextProps) {
  const still = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const rest = settings(axes, 0);
  useProximity(ref, { selector: "[data-index]", axes, enabled: !still });

  if (still) {
    return (
      <Tag id={id} className={className}>
        {text}
      </Tag>
    );
  }

  const pieces = split(text, by);
  let index = 0;
  return (
    <Tag id={id} className={className}>
      <span className="visually-hidden">{text}</span>
      <span ref={ref} className="prox" aria-hidden="true">
        {pieces.map((piece, i) => {
          const gap = by === "word" && i < pieces.length - 1 ? " " : "";
          if (piece.trim() === "") {
            return <span key={i}>{piece}</span>;
          }
          const n = index++;
          return (
            <span key={i}>
              <span className="prox__part" data-index={n} style={{ fontVariationSettings: rest }}>
                {piece}
              </span>
              {gap}
            </span>
          );
        })}
      </span>
    </Tag>
  );
}
