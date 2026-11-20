/**
 * Reloj del fondo ambiental. Solo avanza con los cuadros dibujados (no corre con la pestaña oculta)
 * y da la vuelta cada `TIME_WRAP` segundos: valores pequeños mantienen la precisión del shader en
 * GPU de celulares. El salto al dar la vuelta (cada 15 min de uso) es un leve cambio de forma.
 */
export const TIME_WRAP = 900;

export function advanceTime(time: number, dtSeconds: number): number {
  return (time + dtSeconds) % TIME_WRAP;
}
