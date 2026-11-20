/** Funciones puras del movimiento: sin DOM, para que se puedan probar y reutilizar. */

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

/** Posición en la ventana → −1…1 en cada eje (x a la derecha, y hacia abajo), recortada. */
export function normalize(
  clientX: number,
  clientY: number,
  width: number,
  height: number,
): { x: number; y: number } {
  return {
    x: clamp((clientX / width) * 2 - 1, -1, 1),
    y: clamp((clientY / height) * 2 - 1, -1, 1),
  };
}

/**
 * Suavizado exponencial independiente de la tasa de cuadros: el mismo recorrido a 30 o a 120 fps.
 * `lambda` alto = respuesta rápida.
 */
export function damp(current: number, target: number, lambda: number, dtSeconds: number): number {
  return target + (current - target) * Math.exp(-lambda * dtSeconds);
}

/**
 * Desplazamiento de un botón «imán» hacia el cursor: proporcional a la distancia dentro del
 * radio (máximo `max` px en el borde) y nulo fuera de él.
 */
export function magnetOffset(
  dx: number,
  dy: number,
  radius = 80,
  max = 8,
): { x: number; y: number } {
  if (Math.hypot(dx, dy) > radius) {
    return { x: 0, y: 0 };
  }
  const scale = max / radius;
  return { x: dx * scale + 0, y: dy * scale + 0 };
}

/** Inclinación hacia el puntero: arriba inclina hacia atrás (rx > 0), derecha gira a la derecha. */
export function tiltFromPointer(x: number, y: number, max: number): { rx: number; ry: number } {
  return { rx: -y * max + 0, ry: x * max + 0 };
}
