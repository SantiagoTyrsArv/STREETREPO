import { preloadOrder } from "./math";
import type { Resolution, SequenceManifest } from "./types";

/** Descargas simultáneas como máximo (no saturar la red del celular). */
const MAX_PARALLEL = 6;

export function frameUrl(baseUrl: string, resolution: Resolution, index: number): string {
  return `${baseUrl}/${resolution}/frame_${String(index + 1).padStart(4, "0")}.webp`;
}

/** Espera a que la imagen esté lista; `decode()` donde exista, el evento `load` donde no. */
function whenReady(image: HTMLImageElement): Promise<void> {
  if (typeof image.decode === "function") {
    return image.decode();
  }
  return new Promise((resolve, reject) => {
    image.addEventListener("load", () => resolve(), { once: true });
    image.addEventListener("error", () => reject(new Error(image.src)), { once: true });
  });
}

export interface FrameLoader {
  start(): void;
  cancel(): void;
  get(index: number): HTMLImageElement | undefined;
  readonly loaded: ReadonlySet<number>;
}

/**
 * Descarga los cuadros en el orden de `preloadOrder` (uno de cada medio segundo primero) y avisa
 * con `onFrame` cada vez que uno está listo para dibujarse.
 */
export function createFrameLoader(
  baseUrl: string,
  manifest: SequenceManifest,
  resolution: Resolution,
  onFrame?: (index: number) => void,
): FrameLoader {
  const images = new Map<number, HTMLImageElement>();
  const loaded = new Set<number>();
  const queue = preloadOrder(manifest.frameCount, manifest.fps / 2);
  let cancelled = false;
  let active = 0;

  const pump = (): void => {
    while (!cancelled && active < MAX_PARALLEL && queue.length > 0) {
      const index = queue.shift();
      if (index === undefined) {
        return;
      }
      active++;
      const image = new Image();
      image.decoding = "async";
      image.src = frameUrl(baseUrl, resolution, index);
      images.set(index, image);
      whenReady(image)
        .then(() => {
          if (!cancelled) {
            loaded.add(index);
            onFrame?.(index);
          }
        })
        .catch(() => {
          // Un cuadro que falla se omite: se dibuja el cargado más cercano.
          images.delete(index);
        })
        .finally(() => {
          active--;
          pump();
        });
    }
  };

  return {
    start: pump,
    cancel() {
      cancelled = true;
      queue.length = 0;
    },
    get: (index) => (loaded.has(index) ? images.get(index) : undefined),
    loaded,
  };
}
