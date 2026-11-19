import Lenis from "lenis";
import { useEffect } from "react";
import { bindAnchorNavigation } from "./anchors";
import { gsap, ScrollTrigger } from "./gsap";

/** Desplazamiento suave con Lenis, sincronizado con ScrollTrigger. */
export function useSmoothScroll(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }
    const lenis = new Lenis({ lerp: 0.08 });
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
    };
  }, [enabled]);
}
