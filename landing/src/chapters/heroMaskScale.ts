/** Tramo del progreso de Apertura en el que la cámara atraviesa las letras. */
export const MASK_UNTIL = 0.3;
/** Escala final: las letras ya cubren toda la pantalla. */
const MASK_MAX = 40;

/**
 * Escala de la máscara de la portada: 1 al cargar y hasta `MASK_MAX` al final del tramo, con
 * aceleración (cúbica): empieza despacio, como una cámara que toma impulso.
 */
export function maskScale(progress: number, until = MASK_UNTIL): number {
  const t = Math.min(1, Math.max(0, progress / until));
  return 1 + (MASK_MAX - 1) * t * t * t;
}
