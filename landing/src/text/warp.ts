import { falloff } from "./proximity";

/**
 * *Warp*: desplazamiento de una palabra que se aleja del puntero. `dx`, `dy` = puntero − centro de
 * la palabra (px). Hasta `max` px y una inclinación proporcional, con la misma caída suave de la
 * proximidad.
 */
export function warpOffset(
  dx: number,
  dy: number,
  radius = 140,
  max = 6,
): { x: number; y: number; skew: number } {
  const d = Math.hypot(dx, dy);
  if (d === 0) return { x: 0, y: 0, skew: 0 };
  const k = falloff(d, radius) * max;
  const x = (-dx / d) * k + 0;
  const y = (-dy / d) * k + 0;
  return { x, y, skew: x * 0.5 + 0 };
}
