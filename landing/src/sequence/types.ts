export type ChapterId = "apertura" | "problema" | "priorizar" | "reparado";

export type Resolution = "desktop" | "mobile";

/** Contenido de `public/media/<capítulo>/manifest.json` (lo genera `scripts/build-sequences`). */
export interface SequenceManifest {
  id: ChapterId;
  fps: number;
  frameCount: number;
  resolutions: Record<Resolution, { width: number; height: number }>;
}
