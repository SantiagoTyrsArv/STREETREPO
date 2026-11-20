/** Colores del fondo ambiental. Los valores salen de `tokens.css`; aquí solo se mezclan. */

export type AmbientAccent = "amber" | "signal" | "repair" | "none";

/** Color en 0–1 por canal (lo que espera WebGL). */
export type Rgb = readonly [number, number, number];

export interface AmbientTokens {
  night: Rgb;
  ink: Rgb;
  amber: Rgb;
  signal: Rgb;
  repair: Rgb;
}

export type AmbientPalette = readonly [Rgb, Rgb, Rgb, Rgb];

export function hexToRgb(hex: string): Rgb {
  const match = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec(hex.trim());
  if (!match) {
    throw new Error(`Color no válido: «${hex}»`);
  }
  return [
    parseInt(match[1] as string, 16) / 255,
    parseInt(match[2] as string, 16) / 255,
    parseInt(match[3] as string, 16) / 255,
  ];
}

export function mixRgb(a: Rgb, b: Rgb, t: number): Rgb {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

/**
 * Cuatro colores, de fondo a luz: la noche domina, la tinta da cuerpo y el acento del capítulo
 * aparece en dos intensidades contenidas (diseño 5.1: un solo acento dominante por escena).
 */
export function paletteFor(accent: AmbientAccent, tokens: AmbientTokens): AmbientPalette {
  const [color, body, light] =
    accent === "none" ? [tokens.signal, 0.12, 0.3] : [tokens[accent], 0.22, 0.5];
  // El cuerpo tiñe la tinta (no la noche): con el ámbar evita el tono oliva de mezclarlo con azul.
  return [
    tokens.night,
    tokens.ink,
    mixRgb(tokens.ink, color, body),
    mixRgb(tokens.night, color, light),
  ];
}

/** El acento de la sección que más ocupa la pantalla; `"none"` si no se ve ninguna. */
export function dominantAccent(
  entries: readonly { accent: AmbientAccent; ratio: number }[],
): AmbientAccent {
  let best: AmbientAccent = "none";
  let bestRatio = 0;
  for (const { accent, ratio } of entries) {
    if (ratio > bestRatio) {
      best = accent;
      bestRatio = ratio;
    }
  }
  return best;
}
