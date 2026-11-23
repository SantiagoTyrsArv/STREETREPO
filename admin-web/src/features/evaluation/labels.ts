import type { BlindCard, ServicePoint } from "./api";

const SERVICE_LABELS: Record<ServicePoint["type"], string> = {
  escuela: "Escuela",
  hospital: "Hospital",
};

/** Nombre con el que se identifica una tarjeta: su vía, porque el evaluador no ve más datos. */
export function cardLabel(card: BlindCard): string {
  return card.road_name ?? "Vía sin nombre";
}

export function serviceLabel(service: ServicePoint): string {
  const type = SERVICE_LABELS[service.type];
  return service.name ? `${service.name} · ${type}` : type;
}
