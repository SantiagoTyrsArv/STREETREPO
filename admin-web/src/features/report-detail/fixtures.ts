import type { AdminReport } from "./api";

export const REPORT_ID = "11111111-1111-4111-8111-111111111111";

/** Reporte de ejemplo del diseño (guía 8.3), solo como fixture. */
export const EVALUATED_REPORT: AdminReport = {
  id: REPORT_ID,
  status: "evaluado",
  allowed_next_statuses: ["priorizado", "reparado"],
  severity: "alta",
  description: "Hueco profundo frente a la entrada del colegio.",
  location: { lat: 1.2136, lon: -77.2811 },
  address: "Av. Los Estudiantes",
  needs_road_review: false,
  road: { name: "Av. Los Estudiantes", highway: "secondary" },
  reporter_name: "Camila Ortega",
  created_at: "2026-10-12T15:00:00Z",
  confirmations: 4,
  evaluation: {
    s: 10,
    f: 7,
    p: 8,
    u: 8.7,
    w_severity: 0.5,
    w_flow: 0.3,
    w_proximity: 0.2,
    config_id: 3,
    service: { name: "I. E. M. Ciudad de Pasto", service_type: "escuela", distance_m: 180 },
    calculated_at: "2026-10-13T21:05:00Z",
  },
  history: [
    {
      previous_status: null,
      status: "registrado",
      changed_at: "2026-10-12T15:00:00Z",
      note: null,
      changed_by_name: "Camila Ortega",
    },
    {
      previous_status: "registrado",
      status: "evaluado",
      changed_at: "2026-10-13T21:05:00Z",
      note: null,
      changed_by_name: null,
    },
  ],
};

/** Sin vía a 30 m y sin servicio crítico a 500 m (caso «Sector Obonuco»). */
export const NO_ROAD_REPORT: AdminReport = {
  ...EVALUATED_REPORT,
  address: "Sin vía asociada",
  needs_road_review: true,
  road: null,
  severity: "media",
  description: null,
  confirmations: 0,
  evaluation: {
    ...EVALUATED_REPORT.evaluation!,
    s: 6,
    f: 2,
    p: 0,
    u: 3.6,
    service: null,
  },
};
