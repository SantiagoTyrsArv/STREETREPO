import { useEffect, useRef, useState } from "react";
import { coverRect, frameIndexForProgress, nearestLoaded, pickResolution } from "./math";
import { createFrameLoader, type FrameLoader } from "./loader";
import type { ChapterId, Resolution, SequenceManifest } from "./types";
import "./FrameSequence.css";

/** Densidad máxima del lienzo: más allá no se nota y cuesta memoria en el celular. */
const MAX_DPR = 2;

interface FrameSequenceProps {
  chapter: ChapterId;
  /** Progreso del capítulo entre 0 y 1. */
  progress: number;
  alt: string;
  /** Con `true` descarga los cuadros; antes solo se ve el cuadro clave. */
  load: boolean;
  /** Se llama una vez, cuando todos los cuadros están cargados. */
  onReady?: () => void;
}

function currentResolution(): Resolution {
  return pickResolution(window.innerWidth, window.innerHeight);
}

/**
 * Secuencia de cuadros dibujada en un lienzo según el progreso del *scroll*. Debajo siempre está
 * el cuadro clave (`key.webp`), de modo que con red lenta o sin manifiesto nunca queda vacío.
 */
export function FrameSequence({ chapter, progress, alt, load, onReady }: FrameSequenceProps) {
  const baseUrl = `/media/${chapter}`;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const loaderRef = useRef<FrameLoader | null>(null);
  const progressRef = useRef(progress);
  const [manifest, setManifest] = useState<SequenceManifest | null>(null);
  const [resolution, setResolution] = useState<Resolution>(currentResolution);
  const [loadedCount, setLoadedCount] = useState(0);
  const onReadyRef = useRef(onReady);
  const readySent = useRef(false);

  progressRef.current = progress;
  onReadyRef.current = onReady;

  useEffect(() => {
    let alive = true;
    fetch(`${baseUrl}/manifest.json`)
      .then((response) => (response.ok ? (response.json() as Promise<SequenceManifest>) : null))
      .then((data) => {
        if (alive) {
          setManifest(data);
        }
      })
      .catch(() => {
        // Sin manifiesto se queda el cuadro clave.
      });
    return () => {
      alive = false;
    };
  }, [baseUrl]);

  useEffect(() => {
    const onResize = (): void => setResolution(currentResolution());
    window.addEventListener("resize", onResize);
    window.addEventListener("orientationchange", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("orientationchange", onResize);
    };
  }, []);

  useEffect(() => {
    if (!manifest || !load) {
      return undefined;
    }
    const loader = createFrameLoader(baseUrl, manifest, resolution, () =>
      setLoadedCount((count) => count + 1),
    );
    loaderRef.current = loader;
    loader.start();
    return () => {
      loader.cancel();
      loaderRef.current = null;
    };
  }, [baseUrl, manifest, resolution, load]);

  useEffect(() => {
    const loader = loaderRef.current;
    if (!manifest || !loader || readySent.current) return;
    if (loader.loaded.size >= manifest.frameCount) {
      readySent.current = true;
      onReadyRef.current?.();
    }
  }, [manifest, loadedCount]);

  const target = manifest ? frameIndexForProgress(progress, manifest.frameCount) : 0;

  useEffect(() => {
    const canvas = canvasRef.current;
    const loader = loaderRef.current;
    if (!canvas || !loader) {
      return undefined;
    }
    const frame = requestAnimationFrame(() => {
      const index = loader.loaded.has(target) ? target : nearestLoaded(target, loader.loaded);
      const image = index === null ? undefined : loader.get(index);
      const context = canvas.getContext("2d");
      if (!image || !context) {
        return;
      }
      const dpr = Math.min(MAX_DPR, window.devicePixelRatio || 1);
      const width = Math.round(canvas.clientWidth * dpr);
      const height = Math.round(canvas.clientHeight * dpr);
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      const { sx, sy, sw, sh } = coverRect(image.naturalWidth, image.naturalHeight, width, height);
      context.drawImage(image, sx, sy, sw, sh, 0, 0, width, height);
      canvas.dataset.ready = "true";
    });
    return () => cancelAnimationFrame(frame);
  });

  return (
    <div className="frame-sequence" role="img" aria-label={alt}>
      <img className="frame-sequence__poster" src={`${baseUrl}/key.webp`} alt="" decoding="async" />
      <canvas ref={canvasRef} className="frame-sequence__canvas" aria-hidden="true" />
    </div>
  );
}
