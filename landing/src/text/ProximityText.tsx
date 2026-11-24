import gsap from "gsap";
import { Fragment, useEffect, useRef, type ElementType, type RefObject } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { damp } from "../interaction/motion";
import { pointer, startPointerTracking } from "../interaction/pointer";
import { trackVisibility } from "../interaction/visibility";
import { measureCenters } from "./measure";
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

/**
 * Pasos de cada eje: el navegador dibuja de nuevo las letras con cada valor distinto, así que se
 * escalonan (a la vista sigue siendo progresivo y casi ningún cuadro cambia algo).
 */
const WGHT_STEP = 50;
const WDTH_STEP = 5;

const snap = (value: number, step: number) => Math.round(value / step) * step;

function settings(axes: ProximityAxes, t: number): string {
  const wght = snap(axes.wght[0] + (axes.wght[1] - axes.wght[0]) * t, WGHT_STEP);
  if (!axes.wdth) return `"wght" ${wght}`;
  const wdth = snap(axes.wdth[0] + (axes.wdth[1] - axes.wdth[0]) * t, WDTH_STEP);
  return `"wght" ${wght}, "wdth" ${wdth}`;
}

/**
 * Aplica *variable proximity* a las partes de `ref` que cumplen `selector` (letras o palabras ya
 * partidas): cada una se engrosa (y se ensancha) cuanto más cerca está el puntero o el dedo
 * apoyado, y vuelve exactamente al reposo al alejarse o soltar.
 */
export function useProximity(
  ref: RefObject<HTMLElement | null>,
  {
    selector,
    axes,
    enabled,
    mode = "font",
  }: {
    selector: string;
    axes: ProximityAxes;
    enabled: boolean;
    /**
     * «font»: cambia grosor y ancho (textos cortos). «glow»: solo aclara la palabra con `--near`
     * (0–1). En párrafos el grosor obliga a recomponer todo el texto en cada cuadro y traba el
     * celular; el brillo es solo pintura.
     */
    mode?: "font" | "glow";
  },
): void {
  const axesKey = JSON.stringify(axes);
  useEffect(() => {
    const root = ref.current;
    if (!enabled || !root) return;
    const ax = JSON.parse(axesKey) as ProximityAxes;
    const rest = mode === "glow" ? "" : settings(ax, 0);
    const parts = [...root.querySelectorAll<HTMLElement>(selector)];
    if (parts.length === 0) return;
    const stopTracking = startPointerTracking();
    const view = trackVisibility(root);
    // Centros de cada parte respecto al contenedor: se miden al montar y al cambiar el tamaño, no
    // en cada cuadro (en cada cuadro solo se lee la posición del contenedor).
    let centers: { x: number; y: number }[] = [];
    const measure = () => {
      centers = measureCenters(root, parts);
    };
    measure();
    window.addEventListener("resize", measure, { passive: true });
    const amount = parts.map(() => 0);
    const written = parts.map(() => rest);
    if (mode === "font") {
      parts.forEach((part) => {
        part.style.fontVariationSettings = rest;
      });
    }

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
        const value = mode === "glow" ? (next === 0 ? "" : next.toFixed(2)) : settings(ax, next);
        if (value !== written[i]) {
          written[i] = value;
          if (mode === "glow") {
            if (value === "") part.style.removeProperty("--near");
            else part.style.setProperty("--near", value);
          } else {
            part.style.fontVariationSettings = value;
          }
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
        part.style.removeProperty("--near");
      });
    };
  }, [ref, selector, axesKey, enabled, mode]);
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
  // Por palabra son párrafos: solo brillo (el grosor recompondría todo el párrafo en cada cuadro).
  const mode = by === "word" ? "glow" : "font";
  useProximity(ref, { selector: "[data-index]", axes, enabled: !still, mode });

  if (still) {
    return (
      <Tag id={id} className={className}>
        {text}
      </Tag>
    );
  }

  let index = 0;
  const part = (piece: string, key: number) => (
    <span
      key={key}
      className="prox__part"
      data-index={index++}
      style={mode === "font" ? { fontVariationSettings: settings(axes, 0) } : undefined}
    >
      {piece}
    </span>
  );
  const words = text.split(" ");
  return (
    <Tag id={id} className={className}>
      <span className="visually-hidden">{text}</span>
      <span ref={ref} className="prox" aria-hidden="true">
        {words.map((word, w) => (
          <Fragment key={w}>
            {/* Por letra, las letras de una palabra van juntas: nunca se corta a mitad de palabra. */}
            {by === "word" ? (
              part(word, w)
            ) : (
              <span className="prox__word">{[...word].map(part)}</span>
            )}
            {w < words.length - 1 ? " " : null}
          </Fragment>
        ))}
      </span>
    </Tag>
  );
}
