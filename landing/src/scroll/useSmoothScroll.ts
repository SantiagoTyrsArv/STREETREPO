import Lenis from "lenis";
import { useEffect } from "react";
import { bindAnchorNavigation } from "./anchors";
import { gsap, ScrollTrigger } from "./gsap";

let current: Lenis | null = null;

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
    const unbindAnchors = bindAnchorNavigation(document, (target) =>
      lenis.scrollTo(target, { immediate: true, force: true }),
    );
    return () => {
      unbindAnchors();
      gsap.ticker.remove(tick);
      lenis.destroy();
      if (current === lenis) current = null;
    };
  }, [enabled]);
}
