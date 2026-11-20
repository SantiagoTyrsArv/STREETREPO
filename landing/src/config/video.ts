/**
 * Video promocional (diseño 2026-11-20, 6.9). Mientras sea `null` no aparece nada del video en la
 * página. Para publicarlo: subirlo a YouTube, poner aquí su ID, guardar la portada en
 * `public/media/video/poster.webp` y marcar `aiGenerated` si es una recreación con IA
 * (`landing/media/README.md`).
 */
export interface PromoVideo {
  youtubeId: string;
  title: string;
  /** Portada local (WebP 16:9): YouTube solo carga al tocar reproducir. */
  poster: string;
  /** Muestra «Recreación generada con IA» (decisiones 85 y 90). */
  aiGenerated: boolean;
}

export const VIDEO: PromoVideo | null = null;
