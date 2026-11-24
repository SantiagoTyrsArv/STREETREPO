import gsap from "gsap";
import { useEffect, type RefObject } from "react";
import { damp, tiltFromPointer } from "./motion";
import { pointer, startPointerTracking } from "./pointer";
import { trackVisibility } from "./visibility";

const TILT_LAMBDA = 5;

export interface TiltOptions {
  enabled: boolean;
  /** Inclinación máxima, en grados. */
  maxDeg?: number;
}

const deg = (value: number) => `${Number(value.toFixed(2)) + 0}deg`;

/**
 * Inclinación 3D hacia el puntero o el dedo (de frente en reposo). Publica además
 * `--tilt-x`/`--tilt-y` (−1…1) para que el CSS mueva un reflejo en sentido contrario.
 */
export function useTilt(
  ref: RefObject<HTMLElement | null>,
  { enabled, maxDeg = 4 }: TiltOptions,
): void {
  useEffect(() => {
    const el = ref.current;
    if (!enabled || !el) return;
    const stopTracking = startPointerTracking();
    const view = trackVisibility(el);
    let rx = 0;
    let ry = 0;
    let written = "";

    const tick = (_time: number, deltaMs: number) => {
      if (!view.visible) return;
      const dt = Math.min(deltaMs / 1000, 0.1);
      const goal = pointer.active
        ? tiltFromPointer(pointer.x, pointer.y, maxDeg)
        : { rx: 0, ry: 0 };
      rx = damp(rx, goal.rx, TILT_LAMBDA, dt);
      ry = damp(ry, goal.ry, TILT_LAMBDA, dt);
      const next = `perspective(1200px) rotateX(${deg(rx)}) rotateY(${deg(ry)})`;
      // En reposo el valor no cambia: no se toca el DOM.
      if (next === written) return;
      written = next;
      el.style.transform = next;
      el.style.setProperty("--tilt-x", (ry / maxDeg).toFixed(3));
      el.style.setProperty("--tilt-y", (-rx / maxDeg).toFixed(3));
    };
    gsap.ticker.add(tick);

    return () => {
      gsap.ticker.remove(tick);
      stopTracking();
      view.stop();
      el.style.transform = "";
      el.style.removeProperty("--tilt-x");
      el.style.removeProperty("--tilt-y");
    };
  }, [ref, enabled, maxDeg]);
}
