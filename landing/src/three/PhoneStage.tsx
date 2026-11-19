import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { isWebGLAvailable } from "./isWebGLAvailable";
import type { PhoneScreen } from "./types";
import "./PhoneStage.css";

const PhoneCanvas = lazy(() => import("./PhoneCanvas"));

/** Tramo del progreso en el que se reparten las capturas (antes entra el teléfono, después sale). */
const SCREENS_FROM = 0.1;
const SCREENS_TO = 0.9;

/** Índice de la captura que corresponde a un progreso (0–1). */
export function screenIndexForProgress(progress: number, count: number): number {
  const t = (progress - SCREENS_FROM) / (SCREENS_TO - SCREENS_FROM);
  return Math.min(count - 1, Math.max(0, Math.floor(t * count)));
}

/** Se monta el lienzo cuando el capítulo está a una pantalla o menos. */
function useNearViewport(enabled: boolean) {
  const ref = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(false);
  useEffect(() => {
    const element = ref.current;
    if (!enabled || !element || typeof IntersectionObserver !== "function") {
      return undefined;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setNear(true);
          observer.disconnect();
        }
      },
      { rootMargin: "100% 0px" },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [enabled]);
  return { ref, near };
}

interface PhoneStageProps {
  progress: number;
  screens: readonly PhoneScreen[];
}

export function PhoneStage({ progress, screens }: PhoneStageProps) {
  const still = useReducedMotion();
  const [webgl] = useState(isWebGLAvailable);
  const live = webgl && !still;
  const { ref, near } = useNearViewport(live);
  const index = still ? 0 : screenIndexForProgress(progress, screens.length);
  const current = screens[index];
  if (!current) {
    return null;
  }

  return (
    <div ref={ref} className="phone-stage">
      {live && near ? (
        <>
          <Suspense fallback={null}>
            <PhoneCanvas progress={progress} screens={screens} index={index} />
          </Suspense>
          {/* El lienzo es decorativo; el lector de pantalla recibe la captura que se ve. */}
          <p className="visually-hidden" aria-live="polite">
            {current.alt}
          </p>
        </>
      ) : (
        <div className="phone-stage__flat">
          <img src={current.src} alt={current.alt} width={1080} height={2264} loading="lazy" />
        </div>
      )}
    </div>
  );
}
