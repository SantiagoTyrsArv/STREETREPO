import { useEffect } from "react";
import { normalize } from "./motion";

export interface PointerState {
  /** −1 (izquierda) … 1 (derecha). */
  x: number;
  /** −1 (arriba) … 1 (abajo). */
  y: number;
  /** Hay un mouse sobre la ventana o un dedo tocando la pantalla. */
  active: boolean;
  /** El último puntero fue táctil. */
  touch: boolean;
  /** Rapidez del último movimiento, en anchos de ventana por segundo (sin suavizar). */
  speed: number;
  /** Último toque o clic, con `time` de `performance.now()`. */
  tap: { x: number; y: number; time: number } | null;
}

const state: PointerState = { x: 0, y: 0, active: false, touch: false, speed: 0, tap: null };

/**
 * Estado del puntero compartido por todas las piezas que reaccionan al mouse o al dedo.
 * Se lee en cada cuadro (sin re-renderizar React); solo este módulo lo escribe.
 */
export const pointer: Readonly<PointerState> = state;

let lastMoveTime = 0;

function place(event: PointerEvent): void {
  const next = normalize(event.clientX, event.clientY, window.innerWidth, window.innerHeight);
  const now = performance.now();
  const dt = (now - lastMoveTime) / 1000;
  // Distancia en «medias ventanas» (el rango −1…1 mide 2) por segundo.
  state.speed =
    lastMoveTime > 0
      ? Math.hypot(next.x - state.x, next.y - state.y) / 2 / Math.max(dt, 1 / 240)
      : 0;
  lastMoveTime = now;
  state.x = next.x;
  state.y = next.y;
  state.touch = event.pointerType === "touch";
}

function onMove(event: PointerEvent): void {
  // Un dedo que solo pasa sin tocar no existe; un mouse en la ventana sí cuenta.
  if (event.pointerType === "touch" && !state.active) {
    return;
  }
  place(event);
  state.active = true;
}

function onDown(event: PointerEvent): void {
  place(event);
  state.speed = 0;
  state.active = true;
  state.tap = { x: state.x, y: state.y, time: performance.now() };
}

function onUp(event: PointerEvent): void {
  if (event.pointerType !== "mouse") {
    state.active = false;
  }
}

function onCancel(): void {
  state.active = false;
}

function onMouseOut(event: MouseEvent): void {
  if (event.relatedTarget === null) {
    state.active = false;
  }
}

function reset(): void {
  Object.assign(state, { x: 0, y: 0, active: false, touch: false, speed: 0, tap: null });
  lastMoveTime = 0;
}

const PASSIVE: AddEventListenerOptions = { passive: true };
let users = 0;

/**
 * Empieza a seguir el puntero (un solo juego de escuchadores pasivos para toda la página, con
 * conteo de referencias). Devuelve la función que deja de seguirlo.
 */
export function startPointerTracking(): () => void {
  if (users === 0) {
    window.addEventListener("pointermove", onMove, PASSIVE);
    window.addEventListener("pointerdown", onDown, PASSIVE);
    window.addEventListener("pointerup", onUp, PASSIVE);
    window.addEventListener("pointercancel", onCancel, PASSIVE);
    window.addEventListener("mouseout", onMouseOut, PASSIVE);
    window.addEventListener("blur", onCancel, PASSIVE);
  }
  users++;
  let stopped = false;
  return () => {
    if (stopped) {
      return;
    }
    stopped = true;
    users--;
    if (users === 0) {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerdown", onDown);
      window.removeEventListener("pointerup", onUp);
      window.removeEventListener("pointercancel", onCancel);
      window.removeEventListener("mouseout", onMouseOut);
      window.removeEventListener("blur", onCancel);
      reset();
    }
  };
}

/** Sigue el puntero mientras `enabled` (p. ej. sin movimiento reducido). */
export function usePointerTracking(enabled: boolean): void {
  useEffect(() => (enabled ? startPointerTracking() : undefined), [enabled]);
}
