/**
 * Lectura de pesos escritos a mano. Todo se maneja en centésimas enteras: sumar `0.1 + 0.2`
 * con decimales binarios no da `0.3`, y los pesos deben sumar exactamente 1,00 (guía 2.2).
 */

const HUNDREDTHS_PER_UNIT = 100;
export const WEIGHT_TOTAL_HUNDREDTHS = HUNDREDTHS_PER_UNIT;
const MAX_DECIMALS = 2;
/** Enteros con hasta dos decimales, con coma o punto. Sin signo ni notación científica. */
const WEIGHT_PATTERN = /^(\d+)(?:[.,](\d{1,2}))?$/;

/** Centésimas de un peso entre 0 y 1 (`"0,5"` → 50); `null` si el texto no es un peso válido. */
export function toHundredths(text: string): number | null {
  const match = WEIGHT_PATTERN.exec(text.trim());
  if (!match) {
    return null;
  }
  const [, whole = "", fraction = ""] = match;
  const hundredths =
    Number(whole) * HUNDREDTHS_PER_UNIT + Number(fraction.padEnd(MAX_DECIMALS, "0"));
  return hundredths <= WEIGHT_TOTAL_HUNDREDTHS ? hundredths : null;
}

/** Centésimas → cadena para la API, con punto y dos decimales (50 → `"0.50"`). */
export function hundredthsToApi(hundredths: number): string {
  const whole = Math.floor(hundredths / HUNDREDTHS_PER_UNIT);
  const fraction = String(hundredths % HUNDREDTHS_PER_UNIT).padStart(MAX_DECIMALS, "0");
  return `${whole}.${fraction}`;
}

/** Normaliza un peso escrito a mano: `"0,5"` → `"0.50"`; `null` si no es válido. */
export function parseWeight(text: string): string | null {
  const hundredths = toHundredths(text);
  return hundredths === null ? null : hundredthsToApi(hundredths);
}

/** Suma en centésimas; `null` si algún peso no es válido. */
export function sumHundredths(texts: readonly string[]): number | null {
  let total = 0;
  for (const text of texts) {
    const hundredths = toHundredths(text);
    if (hundredths === null) {
      return null;
    }
    total += hundredths;
  }
  return total;
}
