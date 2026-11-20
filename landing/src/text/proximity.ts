/**
 * Caída de un efecto con la distancia al puntero: 1 encima, 0 desde `radius`, con una curva suave
 * (smoothstep) para que no haya saltos en el borde.
 */
export function falloff(distance: number, radius = 140): number {
  const t = Math.min(1, Math.max(0, 1 - distance / radius));
  return t * t * (3 - 2 * t);
}

/** Ejes de cada tipo de texto (diseño 6.4): reposo → bajo el puntero. */
export const KICKER_AXES = { wght: [700, 900], wdth: [100, 115] } as const;
export const HEADER_CTA_AXES = { wght: [700, 900], wdth: [100, 112] } as const;
export const DOWNLOAD_CTA_AXES = { wght: [800, 900], wdth: [100, 108] } as const;
export const LEAD_AXES = { wght: [400, 600] } as const;
