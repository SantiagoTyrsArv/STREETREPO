import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useReducedMotion } from "../a11y/useReducedMotion";
import { usePointerTracking } from "../interaction/pointer";
import { trackVisibility } from "../interaction/visibility";
import { useClientCheck } from "../lib/useClientCheck";
import { isWebGLAvailable } from "./isWebGLAvailable";
import type { PhoneScreen } from "./types";
import "./PhoneStage.css";

const PhoneCanvas = lazy(() => import("./PhoneCanvas"));

/** Tramo del progreso en el que se reparten las capturas (antes entra el teléfono). */
const SCREENS_FROM = 0.1;
const SCREENS_TO = 0.62;
/** Tramo en el que se abre el abanico de tres teléfonos (último tercio, diseño 6.10). */
export const FAN_FROM = 0.66;
const FAN_TO = 0.94;
/** Giro de cada teléfono lateral del abanico, en grados (± ~18°, diseño 6.10). */
export const FAN_ANGLE_DEG = 18;

/** Apertura del abanico (0 cerrado, 1 abierto) para un progreso, con frenado al final. */
export function fanOpening(progress: number): number {
  const t = Math.min(1, Math.max(0, (progress - FAN_FROM) / (FAN_TO - FAN_FROM)));
  return 1 - (1 - t) ** 3;
}

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
  /** Pantallas de los dos teléfonos del abanico (izquierda y derecha). */
  fan?: readonly PhoneScreen[];
  /** Descripción accesible de los tres teléfonos en abanico. */
  fanCaption?: string;
}

export function PhoneStage({ progress, screens, fan = [], fanCaption }: PhoneStageProps) {
  const still = useReducedMotion();
  const webgl = useClientCheck(isWebGLAvailable);
  const live = webgl && !still;
  const { ref, near } = useNearViewport(live);
  usePointerTracking(live && near);
  // Si el lienzo está en pantalla (el teléfono no dibuja con el mouse cuando ya se pasó Reportar).
  const view = useRef<{ readonly visible: boolean; stop(): void } | null>(null);
  useEffect(() => {
    const element = ref.current;
    if (!live || !near || !element) return undefined;
    view.current = trackVisibility(element);
    return () => {
      view.current?.stop();
      view.current = null;
    };
  }, [live, near, ref]);
  const isVisible = useCallback(() => view.current?.visible ?? true, []);
  const index = still ? 0 : screenIndexForProgress(progress, screens.length);
  const opening = still ? 0 : fanOpening(progress);
  const current = screens[index];
  if (!current) {
    return null;
  }

  return (
    <div ref={ref} className="phone-stage">
      {live && near ? (
        <>
          <Suspense fallback={null}>
            <PhoneCanvas
              progress={progress}
              screens={screens}
              index={index}
              fan={fan}
              opening={opening}
              isVisible={isVisible}
            />
          </Suspense>
          {/* El lienzo es decorativo; el lector de pantalla recibe la captura que se ve. */}
          <p className="visually-hidden" aria-live="polite">
            {opening > 0 && fanCaption ? fanCaption : current.alt}
          </p>
        </>
      ) : (
        <div className="phone-stage__flat">
          {/* Sin WebGL el abanico se arma con las capturas planas; con movimiento reducido, no. */}
          {opening > 0
            ? fan.slice(0, 2).map((screen, i) => (
                <img
                  key={screen.src}
                  className="phone-stage__fan"
                  src={screen.src}
                  alt={screen.alt}
                  width={1080}
                  height={2264}
                  loading="lazy"
                  style={{
                    transform: `translateX(${(i === 0 ? -1 : 1) * 38 * opening}%) rotate(${
                      (i === 0 ? -1 : 1) * FAN_ANGLE_DEG * opening
                    }deg) scale(0.92)`,
                    opacity: Math.min(1, opening * 2),
                  }}
                />
              ))
            : null}
          <img
            className="phone-stage__main"
            src={current.src}
            alt={current.alt}
            width={1080}
            height={2264}
            loading="lazy"
          />
        </div>
      )}
    </div>
  );
}
