/**
 * Réplica didáctica del modelo de urgencia para la página de presentación (diseño 2026-11-20,
 * 6.6). Sigue las reglas de AGENTS.md 2.2 y se prueba con la tabla de la guía 8.3; el cálculo del
 * sistema vive en el backend (`priority/domain`). Todo se calcula en centésimas enteras para no
 * arrastrar errores de coma flotante.
 */

export type Severity = "baja" | "media" | "alta";
export type RoadKind = "principal" | "secundaria" | "terciaria" | "residencial" | "sin-via";

export const DEFAULT_WEIGHTS = { s: 0.5, f: 0.3, p: 0.2 } as const;

const SEVERITY: Record<Severity, number> = { baja: 3, media: 6, alta: 10 };
const FLOW: Record<RoadKind, number> = {
  principal: 10,
  secundaria: 7,
  terciaria: 5,
  residencial: 2,
  "sin-via": 2,
};

/** Radio con P = 10 y radio máximo de proximidad (guía 2.3), en metros. */
const FULL_UNTIL_M = 100;
const ZERO_FROM_M = 500;

/** Mitad hacia arriba para un cociente positivo de enteros. */
function divHalfUp(numerator: number, denominator: number): number {
  return Math.floor((2 * numerator + denominator) / (2 * denominator));
}

export function severityScore(s: Severity): number {
  return SEVERITY[s];
}

export function flowScore(r: RoadKind): number {
  return FLOW[r];
}

/** P (0–10, dos decimales) a partir de la distancia, redondeada a centímetros. */
export function proximityScore(distanceM: number): number {
  const cm = Math.round(distanceM * 100);
  if (cm <= FULL_UNTIL_M * 100) return 10;
  if (cm >= ZERO_FROM_M * 100) return 0;
  // P = 10·(500 − d)/400 → en centésimas: (50 000 − d_cm) / 40.
  return divHalfUp(ZERO_FROM_M * 100 - cm, (ZERO_FROM_M - FULL_UNTIL_M) / 10) / 100;
}

/** U = w₁·S + w₂·F + w₃·P con dos decimales, mitad hacia arriba. */
export function urgency(
  scores: { s: number; f: number; p: number },
  weights: { s: number; f: number; p: number } = DEFAULT_WEIGHTS,
): number {
  const c = (n: number) => Math.round(n * 100);
  const total =
    c(weights.s) * c(scores.s) + c(weights.f) * c(scores.f) + c(weights.p) * c(scores.p);
  return divHalfUp(total, 100) / 100;
}

export function formatDecimal(n: number): string {
  return n.toFixed(2).replace(".", ",");
}
