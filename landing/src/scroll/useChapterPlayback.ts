import { useEffect, useState, type RefObject } from "react";
import { gsap, ScrollTrigger } from "./gsap";
import { MAX_FRAME_WAIT_MS, NEAR_START, shouldStart, TRIGGER_END, TRIGGER_START } from "./playback";

interface PlaybackOptions {
  /** Duración de la reproducción del capítulo. */
  durationMs: number;
  /** Con `false` (movimiento reducido) el capítulo queda en su estado final, sin disparadores. */
  enabled: boolean;
  /** `true` cuando los cuadros de la escena están cargados. */
  ready: boolean;
  /** Se reproduce al montar (la portada), sin esperar a entrar. */
  autoplay?: boolean;
  /** Curva de la reproducción (GSAP). */
  ease?: string;
}

interface Playback {
  /** Progreso del capítulo entre 0 y 1; avanza en el tiempo, no con el *scroll*. */
  progress: number;
  /** `true` cuando el capítulo está cerca: es hora de cargar sus cuadros. */
  near: boolean;
}

/**
 * Reproduce un capítulo una sola vez, en el tiempo, cuando entra en la ventana (diseño 4.1).
 * Devuelve el mismo `progress` que antes daba el *scroll*, así los hijos no cambian.
 */
export function useChapterPlayback(
  ref: RefObject<HTMLElement | null>,
  { durationMs, enabled, ready, autoplay = false, ease = "power2.out" }: PlaybackOptions,
): Playback {
  const [progress, setProgress] = useState(0);
  const [near, setNear] = useState(autoplay);
  const [triggered, setTriggered] = useState(autoplay);
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!enabled || autoplay || !element) return undefined;
    const nearTrigger = ScrollTrigger.create({
      trigger: element,
      start: NEAR_START,
      once: true,
      onEnter: () => setNear(true),
    });
    const playTrigger = ScrollTrigger.create({
      trigger: element,
      start: TRIGGER_START,
      end: TRIGGER_END,
      onToggle: (self) => {
        if (self.isActive) setTriggered(true);
      },
    });
    return () => {
      nearTrigger.kill();
      playTrigger.kill();
    };
  }, [ref, enabled, autoplay]);

  useEffect(() => {
    if (!enabled || !triggered || ready) return undefined;
    const timer = setTimeout(() => setTimedOut(true), MAX_FRAME_WAIT_MS);
    return () => clearTimeout(timer);
  }, [enabled, triggered, ready]);

  const waitedMs = timedOut ? MAX_FRAME_WAIT_MS : 0;
  const start = enabled && shouldStart({ triggered, ready, waitedMs });

  useEffect(() => {
    // `start` solo pasa de falso a verdadero (entrar, cuadros listos y tope no se deshacen): una
    // reproducción por carga. Si React desmonta y vuelve a montar (StrictMode), se rehace.
    if (!start) return undefined;
    const state = { value: 0 };
    const tween = gsap.to(state, {
      value: 1,
      duration: durationMs / 1000,
      ease,
      onUpdate: () => setProgress(state.value),
    });
    return () => {
      tween.kill();
    };
  }, [start, durationMs, ease]);

  return enabled ? { progress, near } : { progress: 1, near: false };
}
