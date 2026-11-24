/** Giro de cada teléfono lateral del abanico (≈ 18°, diseño 6.10). */
export const FAN_ANGLE = (18 * Math.PI) / 180;
/** Separación horizontal de los laterales respecto al principal (unidades de la escena). */
export const FAN_SPREAD = 0.58;
/** Margen a cada lado del lienzo. */
const FIT_MARGIN = 0.92;

export interface FanGeometry {
  bodyWidth: number;
  bodyHeight: number;
  /** Escala de los teléfonos laterales. */
  sideScale: number;
}

/**
 * Escala para que el abanico quepa a lo ancho del lienzo (en el celular es angosto): con el
 * abanico cerrado basta el teléfono; abierto, hay que sumar los laterales girados.
 */
export function fanFitScale(opening: number, viewportWidth: number, geometry: FanGeometry): number {
  const { bodyWidth, bodyHeight, sideScale } = geometry;
  const sideHalf =
    sideScale * ((bodyWidth / 2) * Math.cos(FAN_ANGLE) + (bodyHeight / 2) * Math.sin(FAN_ANGLE));
  const closedHalf = bodyWidth / 2;
  const openHalf = FAN_SPREAD + sideHalf;
  const needed = closedHalf + (openHalf - closedHalf) * Math.min(1, Math.max(0, opening));
  return Math.min(1, ((viewportWidth / 2) * FIT_MARGIN) / needed);
}
