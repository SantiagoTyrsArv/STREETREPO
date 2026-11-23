/** Números de los resultados con coma decimal (guía 9.2); el CSV conserva el punto. */
const LOCALE = "es-CO";
const P_VALUE_FLOOR = 0.001;

const twoDecimals = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const threeDecimals = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});
const upToOneDecimal = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 1 });

/** Coeficiente o estadístico: `0.8125` → «0,81». */
export function formatCoefficient(value: number): string {
  return twoDecimals.format(value);
}

/** Valor p: `0.0213` → «p = 0,021»; por debajo de 0,001, «p < 0,001». */
export function formatPValue(value: number): string {
  return value < P_VALUE_FLOOR
    ? `p < ${threeDecimals.format(P_VALUE_FLOOR)}`
    : `p = ${threeDecimals.format(value)}`;
}

/** Porcentaje: `62.5` → «62,5 %». */
export function formatPercent(value: number): string {
  return `${upToOneDecimal.format(value)} %`;
}

/** Posición del panel, que puede ser un rango promedio: `1.5` → «1,5». */
export function formatPosition(value: number): string {
  return upToOneDecimal.format(value);
}

/**
 * Diferencia de posiciones del panel respecto al motor: ▼ si el panel lo ubica más abajo
 * (menos urgente), ▲ si más arriba (Figma «Ranking comparado»).
 */
export function formatShift(motor: number, panel: number): string {
  const shift = panel - motor;
  if (shift === 0) {
    return "Igual";
  }
  return `${shift > 0 ? "▼" : "▲"} ${upToOneDecimal.format(Math.abs(shift))}`;
}
