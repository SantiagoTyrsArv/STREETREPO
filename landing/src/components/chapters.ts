/** Capítulos de la página en orden, con su ancla (`id` de la sección). */
export const CHAPTER_IDS = [
  "apertura",
  "problema",
  "reportar",
  "priorizar",
  "prueba",
  "panel",
  "reparado",
  "descarga",
] as const;

export type ChapterAnchor = (typeof CHAPTER_IDS)[number];

/** El capítulo que contiene la línea media de la ventana; `null` si ninguno. */
export function pickActive(
  entries: readonly { id: string; top: number; height: number }[],
  viewportHeight: number,
): string | null {
  const middle = viewportHeight / 2;
  const hit = entries.find((e) => e.top <= middle && e.top + e.height > middle);
  return hit?.id ?? null;
}
