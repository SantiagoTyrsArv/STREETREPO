/** Datos de prueba de la comparación (objetivo 4): ilustrativos, no son datos de campo. */
import type { Round, RoundProgress, Zone } from "./api";

const square = (lon: number, lat: number) => ({
  type: "Polygon",
  coordinates: [
    [
      [lon, lat],
      [lon + 0.01, lat],
      [lon + 0.01, lat + 0.01],
      [lon, lat + 0.01],
      [lon, lat],
    ],
  ],
});

export const ZONES: Zone[] = [
  {
    id: 1,
    name: "Centro",
    concentration: "alta",
    active_reports: 14,
    total_reports: 18,
    geometry: square(-77.285, 1.21),
  },
  {
    id: 2,
    name: "Obonuco",
    concentration: "baja",
    active_reports: 6,
    total_reports: 7,
    geometry: square(-77.3, 1.195),
  },
];

export const OPEN_ROUND: Round = {
  id: "r-2",
  name: "Piloto 2",
  status: "abierta",
  sample_size: 10,
  opened_at: "2026-11-20T15:00:00Z",
  closed_at: null,
};

export const CLOSED_ROUND: Round = {
  id: "r-1",
  name: "Piloto 1",
  status: "cerrada",
  sample_size: 8,
  opened_at: "2026-11-10T15:00:00Z",
  closed_at: "2026-11-12T20:00:00Z",
};

export const OPEN_PROGRESS: RoundProgress = {
  ...OPEN_ROUND,
  zones: [
    {
      zone_id: 1,
      name: "Centro",
      concentration: "alta",
      n_reports: 10,
      submitted_by: ["Evaluador 1"],
    },
    { zone_id: 2, name: "Obonuco", concentration: "baja", n_reports: 6, submitted_by: [] },
  ],
};
