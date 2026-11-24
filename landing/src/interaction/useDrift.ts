import gsap from "gsap";
import { useEffect, type RefObject } from "react";
import { damp } from "./motion";
import { pointer, startPointerTracking } from "./pointer";
import { trackVisibility } from "./visibility";

/** Suavizado del paralaje (1/s): sigue al puntero con una inercia de cámara. */
const DRIFT_LAMBDA = 4;

export interface DriftOptions {
  enabled: boolean;
  /**
   * Desplazamiento máximo por eje, como fracción del tamaño del elemento. Debe quedar por debajo
   * del margen de la respiración (escala mínima 1,03 → 1,5 % por lado) para no ver los bordes.
   */
  maxShift?: number;
}

const px = (value: number) => `${Number(value.toFixed(2)) + 0}px`;

/**
 * Paralaje: desplaza el elemento hacia el puntero o el dedo (y lo devuelve al centro en reposo).
 * Escribe `transform` en cada cuadro de `gsap.ticker`, sin re-renderizar React.
 */
export function useDrift(
  ref: RefObject<HTMLElement | null>,
  { enabled, maxShift = 0.012 }: DriftOptions,
) {
  useEffect(() => {
    const el = ref.current;
    if (!enabled || !el) return;
    const stopTracking = startPointerTracking();
    const view = trackVisibility(el);
    // El tamaño se lee una vez y se actualiza al cambiar, no en cada cuadro (evita forzar estilos).
    const size = { w: el.offsetWidth, h: el.offsetHeight };
    const resize =
      typeof ResizeObserver === "function"
        ? new ResizeObserver(() => {
            size.w = el.offsetWidth;
            size.h = el.offsetHeight;
          })
        : null;
    resize?.observe(el);
    let x = 0;
    let y = 0;
    let written = "";

    const tick = (_time: number, deltaMs: number) => {
      if (!view.visible) return;
      const dt = Math.min(deltaMs / 1000, 0.1);
      x = damp(x, pointer.active ? pointer.x * size.w * maxShift : 0, DRIFT_LAMBDA, dt);
      y = damp(y, pointer.active ? pointer.y * size.h * maxShift : 0, DRIFT_LAMBDA, dt);
      const next = `translate3d(${px(x)}, ${px(y)}, 0px)`;
      // En reposo el valor no cambia: no se toca el DOM.
      if (next !== written) {
        written = next;
        el.style.transform = next;
      }
    };
    gsap.ticker.add(tick);

    return () => {
      gsap.ticker.remove(tick);
      stopTracking();
      view.stop();
      resize?.disconnect();
      el.style.transform = "";
    };
  }, [ref, enabled, maxShift]);
}
