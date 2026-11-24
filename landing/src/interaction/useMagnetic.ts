import gsap from "gsap";
import { useEffect, type RefObject } from "react";
import { damp, magnetOffset } from "./motion";

/** Solo donde hay un cursor real: en pantallas táctiles el imán no tiene sentido. */
const FINE_POINTER = "(hover: hover) and (pointer: fine)";
const MAGNET_LAMBDA = 10;

const px = (value: number) => `${Number(value.toFixed(2)) + 0}px`;

/**
 * Botón «imán»: se acerca al cursor cuando pasa cerca (radio 80 px, hasta 8 px) y publica en
 * `--spot-x`/`--spot-y` el punto del botón bajo el cursor, para un brillo que lo sigue (CSS).
 */
export function useMagnetic(ref: RefObject<HTMLElement | null>, enabled: boolean): void {
  useEffect(() => {
    const el = ref.current;
    if (!enabled || !el || !window.matchMedia(FINE_POINTER).matches) return;
    const target = { x: 0, y: 0 };
    const current = { x: 0, y: 0 };
    // Sin transform en línea el botón ya está en reposo: no hace falta escribirlo.
    let written = `translate(${px(0)}, ${px(0)})`;

    const onMove = (event: PointerEvent) => {
      // En portátiles con pantalla táctil, el dedo no debe arrastrar el botón.
      if (event.pointerType !== "mouse") return;
      const rect = el.getBoundingClientRect();
      const offset = magnetOffset(
        event.clientX - (rect.left + rect.width / 2),
        event.clientY - (rect.top + rect.height / 2),
      );
      target.x = offset.x;
      target.y = offset.y;
      const sx = ((event.clientX - rect.left) / rect.width) * 100;
      const sy = ((event.clientY - rect.top) / rect.height) * 100;
      el.style.setProperty("--spot-x", `${Math.round(sx)}%`);
      el.style.setProperty("--spot-y", `${Math.round(sy)}%`);
    };
    const onLeave = (event: MouseEvent) => {
      if (event.relatedTarget === null) {
        target.x = 0;
        target.y = 0;
      }
    };
    const tick = (_time: number, deltaMs: number) => {
      const dt = Math.min(deltaMs / 1000, 0.1);
      current.x = damp(current.x, target.x, MAGNET_LAMBDA, dt);
      current.y = damp(current.y, target.y, MAGNET_LAMBDA, dt);
      const next = `translate(${px(current.x)}, ${px(current.y)})`;
      // En reposo el valor no cambia: no se toca el DOM.
      if (next !== written) {
        written = next;
        el.style.transform = next;
      }
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("mouseout", onLeave, { passive: true });
    gsap.ticker.add(tick);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("mouseout", onLeave);
      gsap.ticker.remove(tick);
      el.style.transform = "";
      el.style.removeProperty("--spot-x");
      el.style.removeProperty("--spot-y");
    };
  }, [ref, enabled]);
}
