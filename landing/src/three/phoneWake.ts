/**
 * Clave que cambia cuando el teléfono debe dibujar un cuadro nuevo por el puntero; `null` si el
 * lienzo está fuera de pantalla (entonces no se despierta aunque el mouse se mueva).
 */
export function phoneWakeKey(
  visible: boolean,
  p: { active: boolean; x: number; y: number },
): string | null {
  return visible ? `${p.active}:${p.x}:${p.y}` : null;
}
