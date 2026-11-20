import gsap from "gsap";
import { useEffect, type RefObject } from "react";
import { damp } from "../interaction/motion";
import { pointer, startPointerTracking } from "../interaction/pointer";
import { trackVisibility } from "../interaction/visibility";
import { warpOffset } from "./warp";

const WARP_LAMBDA = 9;
const round = (n: number) => Number(n.toFixed(2)) + 0;

/**
 * *Warp* en las palabras (`.reveal__word`) de un título: se apartan e inclinan cerca del puntero o
 * del dedo y vuelven a su sitio al alejarse. `version` cambia cuando el título se vuelve a partir.
 */
export function useWarp(ref: RefObject<HTMLElement>, enabled: boolean, version: number): void {
  useEffect(() => {
    const root = ref.current;
    if (!enabled || !root) return;
    const words = [...root.querySelectorAll<HTMLElement>(".reveal__word")];
    if (words.length === 0) return;
    const stopTracking = startPointerTracking();
    const view = trackVisibility(root);
    let centers: { x: number; y: number }[] = [];
    const measure = () => {
      const box = root.getBoundingClientRect();
      centers = words.map((w) => {
        const r = w.getBoundingClientRect();
        return { x: r.left + r.width / 2 - box.left, y: r.top + r.height / 2 - box.top };
      });
    };
    measure();
    window.addEventListener("resize", measure, { passive: true });
    const state = words.map(() => ({ x: 0, y: 0, skew: 0, written: "" }));

    const tick = (_time: number, deltaMs: number) => {
      if (!view.visible) return;
      if (!pointer.active && state.every((s) => s.written === "")) return;
      const dt = Math.min(deltaMs / 1000, 0.1);
      const box = root.getBoundingClientRect();
      const px = ((pointer.x + 1) / 2) * window.innerWidth;
      const py = ((pointer.y + 1) / 2) * window.innerHeight;
      words.forEach((word, i) => {
        const c = centers[i];
        const s = state[i];
        if (!c || !s) return;
        const goal = pointer.active
          ? warpOffset(px - (box.left + c.x), py - (box.top + c.y))
          : { x: 0, y: 0, skew: 0 };
        s.x = damp(s.x, goal.x, WARP_LAMBDA, dt);
        s.y = damp(s.y, goal.y, WARP_LAMBDA, dt);
        s.skew = damp(s.skew, goal.skew, WARP_LAMBDA, dt);
        const atRest = Math.abs(s.x) < 0.01 && Math.abs(s.y) < 0.01 && Math.abs(s.skew) < 0.01;
        const next = atRest
          ? ""
          : `translate(${round(s.x)}px, ${round(s.y)}px) skewX(${round(s.skew)}deg)`;
        if (next !== s.written) {
          s.written = next;
          word.style.transform = next;
        }
      });
    };
    gsap.ticker.add(tick);

    return () => {
      gsap.ticker.remove(tick);
      stopTracking();
      view.stop();
      window.removeEventListener("resize", measure);
      words.forEach((w) => {
        w.style.transform = "";
      });
    };
  }, [ref, enabled, version]);
}
