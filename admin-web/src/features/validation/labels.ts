import type { Concentration, Round } from "./api";

const CONCENTRATION_LABELS: Record<Concentration, string> = {
  alta: "Alta concentración",
  baja: "Baja concentración",
};

const ROUND_STATUS_LABELS: Record<Round["status"], string> = {
  abierta: "Abierta",
  cerrada: "Cerrada",
};

export function concentrationLabel(concentration: Concentration): string {
  return CONCENTRATION_LABELS[concentration];
}

export function roundStatusLabel(status: Round["status"]): string {
  return ROUND_STATUS_LABELS[status];
}
