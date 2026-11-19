import { useEffect, useState, type RefObject } from "react";
import { ScrollTrigger } from "./gsap";

interface ChapterProgressOptions {
  /** Largo del recorrido fijado, en porcentaje del alto de la ventana (250 = 2,5 pantallas). */
  pinLengthVh: number;
  /** Con `false` no se fija ni se mide nada (movimiento reducido). */
  enabled: boolean;
}

/** Fija la sección mientras se recorre y devuelve su progreso entre 0 y 1. */
export function useChapterProgress(
  ref: RefObject<HTMLElement | null>,
  { pinLengthVh, enabled }: ChapterProgressOptions,
): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const element = ref.current;
    if (!enabled || !element) {
      return undefined;
    }
    const trigger = ScrollTrigger.create({
      trigger: element,
      start: "top top",
      end: `+=${pinLengthVh}%`,
      pin: true,
      scrub: true,
      onUpdate: (self) => setProgress(self.progress),
    });
    return () => trigger.kill();
  }, [ref, pinLengthVh, enabled]);

  return progress;
}
