import Lenis from "lenis";
import Snap from "lenis/snap";
import { useEffect } from "react";
import { bindAnchorNavigation } from "./anchors";
import { gsap, ScrollTrigger } from "./gsap";

let current: Lenis | null = null;

/**
 * Imán de proximidad (diseño 4.4): al soltar el *scroll* cerca del inicio de un capítulo, la página
 * se acomoda en él. Lejos de un punto no actúa: se puede bajar rápido sin quedar atrapado.
 */
export const SNAP_OPTIONS = { type: "proximity", distanceThreshold: "30%", debounce: 150 } as const;

/** Detiene el desplazamiento suave (p. ej. con una ventana modal abierta). */
export function pauseSmoothScroll(): void {
  current?.stop();
}

/** Reanuda el desplazamiento suave. */
export function resumeSmoothScroll(): void {
  current?.start();
}

/** Desplazamiento suave con Lenis, sincronizado con ScrollTrigger. */
export function useSmoothScroll(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }
    const lenis = new Lenis({ lerp: 0.08 });
    current = lenis;
    lenis.on("scroll", () => ScrollTrigger.update());
    const tick = (time: number): void => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    // Salto inmediato: recorrer suavemente todas las escenas obligaría a cargar sus cuadros.
    const snap = new Snap(lenis, SNAP_OPTIONS);
    document
      .querySelectorAll<HTMLElement>("main > section")
      .forEach((section) => snap.addElement(section, { align: "start" }));
    const unbindAnchors = bindAnchorNavigation(document, (target) =>
      lenis.scrollTo(target, { immediate: true, force: true }),
    );
    return () => {
      unbindAnchors();
      snap.destroy();
      gsap.ticker.remove(tick);
      lenis.destroy();
      if (current === lenis) current = null;
    };
  }, [enabled]);
}
