import type { Resolution } from "./types";

/** Ancho por debajo del cual se usa la versión móvil aunque la pantalla sea horizontal. */
const MOBILE_MAX_WIDTH = 768;

/** Cuadro (0 … frameCount − 1) que corresponde a un progreso del capítulo entre 0 y 1. */
export function frameIndexForProgress(progress: number, frameCount: number): number {
  const clamped = Math.min(1, Math.max(0, progress));
  return Math.min(frameCount - 1, Math.round(clamped * (frameCount - 1)));
}

/**
 * Orden de descarga: el cuadro 0, luego uno de cada `stride` (para tener pronto una versión
 * gruesa de toda la escena) y después el resto.
 */
export function preloadOrder(frameCount: number, stride: number): number[] {
  const step = Math.max(1, Math.floor(stride));
  const coarse: number[] = [];
  const rest: number[] = [];
  for (let i = 0; i < frameCount; i++) {
    (i % step === 0 ? coarse : rest).push(i);
  }
  return [...coarse, ...rest];
}

/** Cuadro cargado más cercano al pedido; en un empate, el anterior. `null` si no hay ninguno. */
export function nearestLoaded(target: number, loaded: ReadonlySet<number>): number | null {
  let best: number | null = null;
  for (const index of loaded) {
    if (best === null) {
      best = index;
      continue;
    }
    const distance = Math.abs(index - target);
    const bestDistance = Math.abs(best - target);
    if (distance < bestDistance || (distance === bestDistance && index < best)) {
      best = index;
    }
  }
  return best;
}

export function pickResolution(viewportWidth: number, viewportHeight: number): Resolution {
  return viewportHeight > viewportWidth || viewportWidth < MOBILE_MAX_WIDTH ? "mobile" : "desktop";
}

/** Región de la fuente que se dibuja para cubrir el destino sin deformar (`object-fit: cover`). */
export function coverRect(
  srcW: number,
  srcH: number,
  dstW: number,
  dstH: number,
): { sx: number; sy: number; sw: number; sh: number } {
  const scale = Math.max(dstW / srcW, dstH / srcH);
  const sw = dstW / scale;
  const sh = dstH / scale;
  return { sx: (srcW - sw) / 2, sy: (srcH - sh) / 2, sw, sh };
}
