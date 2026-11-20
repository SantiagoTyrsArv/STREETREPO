import gsap from "gsap";
import { useEffect, type RefObject } from "react";
import { damp } from "./motion";
import { pointer, startPointerTracking } from "./pointer";

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
export function useDrift(ref: RefObject<HTMLElement>, { enabled, maxShift = 0.012 }: DriftOptions) {
  useEffect(() => {
    const el = ref.current;
    if (!enabled || !el) return;
    const stopTracking = startPointerTracking();
    let x = 0;
    let y = 0;

    const tick = (_time: number, deltaMs: number) => {
      const dt = Math.min(deltaMs / 1000, 0.1);
      x = damp(x, pointer.active ? pointer.x * el.offsetWidth * maxShift : 0, DRIFT_LAMBDA, dt);
      y = damp(y, pointer.active ? pointer.y * el.offsetHeight * maxShift : 0, DRIFT_LAMBDA, dt);
      el.style.transform = `translate3d(${px(x)}, ${px(y)}, 0px)`;
    };
    gsap.ticker.add(tick);

    return () => {
      gsap.ticker.remove(tick);
      stopTracking();
      el.style.transform = "";
    };
  }, [ref, enabled, maxShift]);
}
